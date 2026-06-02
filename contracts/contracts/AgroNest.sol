// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title AgroNest - Contrato unificado para el sistema DeFi agricola
/// @dev Combina: AgroNestCrop (ERC721), MockOracle, CropVault y bCROPToken
///      en un solo contrato para minimizar el gas de despliegue.
///      MockUSDC se mantiene separado por incompatibilidad de selectores ERC20/ERC721.
contract AgroNest is ERC721, Ownable, ReentrancyGuard {

    IERC20 public immutable usdc;

    // ─── NFT / Cosechas ───────────────────────────────────────────────────────

    uint256 private _nextTokenId;

    struct CropMetadata {
        string  farmId;
        uint256 hectares;
        string  grainType;
        uint256 estimatedYieldKg;
        uint256 capitalRequired;
        uint256 harvestDate;
        address farmer;
    }

    mapping(uint256 => CropMetadata) public cropData;

    event CropMinted(
        uint256 indexed tokenId,
        address indexed farmer,
        string  farmId,
        uint256 capitalRequired,
        uint256 harvestDate
    );

    // ─── Oracle / Estados ─────────────────────────────────────────────────────

    enum CropState {
        PLANTED,    // 0
        ACTIVE,     // 1
        MATURE,     // 2
        LIQUIDATED, // 3
        DEFAULTED   // 4
    }

    // ─── Vaults ───────────────────────────────────────────────────────────────

    uint256 private _nextVaultId;

    enum VaultStatus {
        OPEN,       // 0
        FUNDED,     // 1
        LIQUIDATED, // 2
        DEFAULTED   // 3
    }

    struct VaultInfo {
        uint256     cropTokenId;
        uint256     fundingGoal;
        uint256     fundingDeadline;
        uint256     reservePercent;
        uint256     yieldPercent;
        uint256     totalRaised;
        VaultStatus status;
        address     farmerAddress;
        CropState   oracleState;
    }

    mapping(uint256 => VaultInfo) public vaults;

    // bCROP: vaultId => investor => balance
    mapping(uint256 => mapping(address => uint256)) public bCropBalances;
    mapping(uint256 => uint256) public bCropSupply;
    mapping(uint256 => address[]) private _vaultInvestors;
    mapping(uint256 => mapping(address => bool)) private _isVaultInvestor;

    // ─── Eventos ─────────────────────────────────────────────────────────────

    event VaultCreated(
        uint256 indexed vaultId,
        uint256 indexed cropTokenId,
        uint256 fundingGoal,
        uint256 fundingDeadline
    );
    event InvestmentReceived(
        uint256 indexed vaultId,
        address indexed investor,
        uint256 usdcAmount,
        uint256 bCropMinted
    );
    event FundingComplete(
        uint256 indexed vaultId,
        uint256 totalRaised,
        uint256 reserveAmount,
        uint256 disbursedToFarmer
    );
    event CropLiquidated(
        uint256 indexed vaultId,
        uint256 totalPayout,
        uint256 yieldAmount
    );
    event CropDefaulted(
        uint256 indexed vaultId,
        uint256 reserveAvailable
    );
    event ReturnsClaimed(
        uint256 indexed vaultId,
        address indexed investor,
        uint256 usdcAmount
    );
    event StateAdvanced(
        uint256 indexed vaultId,
        CropState newState
    );

    // ─── Constructor ─────────────────────────────────────────────────────────

    constructor(address initialOwner, address _usdc)
        ERC721("AgroNestCrop", "ACROP")
        Ownable(initialOwner)
    {
        usdc = IERC20(_usdc);
    }

    // ─── NFT: AgroNestCrop ────────────────────────────────────────────────────

    /// @notice Mintea un NFT de cosecha. Solo el API wallet (owner) puede llamarlo.
    function mintCrop(
        address   to,
        string    calldata farmId,
        uint256   hectares,
        string    calldata grainType,
        uint256   estimatedYieldKg,
        uint256   capitalRequired,
        uint256   harvestDate
    ) external onlyOwner returns (uint256 tokenId) {
        tokenId = ++_nextTokenId;
        _safeMint(to, tokenId);
        cropData[tokenId] = CropMetadata({
            farmId:           farmId,
            hectares:         hectares,
            grainType:        grainType,
            estimatedYieldKg: estimatedYieldKg,
            capitalRequired:  capitalRequired,
            harvestDate:      harvestDate,
            farmer:           to
        });
        emit CropMinted(tokenId, to, farmId, capitalRequired, harvestDate);
    }

    function getCropData(uint256 tokenId) external view returns (CropMetadata memory) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return cropData[tokenId];
    }

    function totalCrops() external view returns (uint256) {
        return _nextTokenId;
    }

    // ─── Vault ────────────────────────────────────────────────────────────────

    /// @notice Crea una nueva boveda y bloquea el NFT como colateral.
    /// @dev El API wallet (owner) llama esta funcion. No requiere approve del NFT
    ///      porque el contrato usa _transfer() interno sobre su propio ERC721.
    function createVault(
        uint256 cropTokenId,
        uint256 fundingGoal,
        uint256 fundingDeadline,
        uint256 reservePercent,
        uint256 yieldPercent,
        address farmer
    ) external onlyOwner returns (uint256 vaultId) {
        require(reservePercent <= 30, "AgroNest: reserve too high");
        require(yieldPercent <= 100, "AgroNest: yield too high");
        require(fundingGoal > 0, "AgroNest: funding goal must be > 0");

        // Transferir NFT al contrato sin necesidad de approve externo
        _transfer(ownerOf(cropTokenId), address(this), cropTokenId);

        vaultId = ++_nextVaultId;
        vaults[vaultId] = VaultInfo({
            cropTokenId:     cropTokenId,
            fundingGoal:     fundingGoal,
            fundingDeadline: fundingDeadline,
            reservePercent:  reservePercent,
            yieldPercent:    yieldPercent,
            totalRaised:     0,
            status:          VaultStatus.OPEN,
            farmerAddress:   farmer,
            oracleState:     CropState.ACTIVE
        });

        emit VaultCreated(vaultId, cropTokenId, fundingGoal, fundingDeadline);
    }

    /// @notice Deposita USDC en nombre de un inversor y le acredita bCROP internamente.
    /// @dev El API wallet debe haber aprobado este contrato para gastar su USDC antes de llamar.
    function deposit(
        uint256 vaultId,
        uint256 usdcAmount,
        address investor
    ) external nonReentrant onlyOwner {
        VaultInfo storage vault = vaults[vaultId];
        require(vault.status == VaultStatus.OPEN, "AgroNest: vault not open");
        require(block.timestamp <= vault.fundingDeadline, "AgroNest: deadline passed");
        require(usdcAmount > 0, "AgroNest: amount must be > 0");
        require(
            vault.totalRaised + usdcAmount <= vault.fundingGoal,
            "AgroNest: exceeds funding goal"
        );

        usdc.transferFrom(msg.sender, address(this), usdcAmount);

        // Acreditar bCROP (ratio 1:1)
        bCropBalances[vaultId][investor] += usdcAmount;
        bCropSupply[vaultId]             += usdcAmount;

        if (!_isVaultInvestor[vaultId][investor]) {
            _isVaultInvestor[vaultId][investor] = true;
            _vaultInvestors[vaultId].push(investor);
        }

        vault.totalRaised += usdcAmount;

        emit InvestmentReceived(vaultId, investor, usdcAmount, usdcAmount);

        if (vault.totalRaised == vault.fundingGoal) {
            _completeFunding(vaultId);
        }
    }

    function _completeFunding(uint256 vaultId) internal {
        VaultInfo storage vault = vaults[vaultId];
        vault.status = VaultStatus.FUNDED;
        uint256 reserve   = (vault.totalRaised * vault.reservePercent) / 100;
        uint256 disbursed = vault.totalRaised - reserve;
        usdc.transfer(vault.farmerAddress, disbursed);
        emit FundingComplete(vaultId, vault.totalRaised, reserve, disbursed);
    }

    /// @notice Reclama retornos de un inversor (principal + rendimiento o reserva en default).
    function claimReturns(uint256 vaultId, address investor) external nonReentrant onlyOwner {
        VaultInfo storage vault = vaults[vaultId];
        require(
            vault.status == VaultStatus.LIQUIDATED || vault.status == VaultStatus.DEFAULTED,
            "AgroNest: vault not claimable"
        );

        uint256 bCropBalance = bCropBalances[vaultId][investor];
        require(bCropBalance > 0, "AgroNest: no bCROP to redeem");

        uint256 payout;
        if (vault.status == VaultStatus.LIQUIDATED) {
            uint256 yieldPerToken = (vault.yieldPercent * 1e6) / 100;
            payout = bCropBalance + (bCropBalance * yieldPerToken / 1e6);
        } else {
            uint256 reserve = (vault.totalRaised * vault.reservePercent) / 100;
            payout = (bCropBalance * reserve) / vault.totalRaised;
        }

        bCropBalances[vaultId][investor] = 0;
        bCropSupply[vaultId]            -= bCropBalance;

        usdc.transfer(investor, payout);

        emit ReturnsClaimed(vaultId, investor, payout);
    }

    // ─── Oracle ───────────────────────────────────────────────────────────────

    /// @notice Avanza el estado del ciclo de vida de una boveda.
    function advanceState(uint256 vaultId, bool success) external onlyOwner {
        VaultInfo storage vault = vaults[vaultId];
        CropState current = vault.oracleState;

        require(
            current != CropState.LIQUIDATED && current != CropState.DEFAULTED,
            "AgroNest: vault in terminal state"
        );

        CropState newState;

        if (current == CropState.MATURE) {
            if (success) {
                newState = CropState.LIQUIDATED;
                vault.status = VaultStatus.LIQUIDATED;
                uint256 yieldTotal = (vault.totalRaised * vault.yieldPercent) / 100;
                emit CropLiquidated(vaultId, vault.totalRaised, yieldTotal);
            } else {
                newState = CropState.DEFAULTED;
                vault.status = VaultStatus.DEFAULTED;
                uint256 reserve = (vault.totalRaised * vault.reservePercent) / 100;
                emit CropDefaulted(vaultId, reserve);
            }
        } else {
            newState = CropState(uint8(current) + 1);
        }

        vault.oracleState = newState;
        emit StateAdvanced(vaultId, newState);
    }

    function getOracleState(uint256 vaultId) external view returns (CropState) {
        return vaults[vaultId].oracleState;
    }

    // ─── Vistas ───────────────────────────────────────────────────────────────

    function getVaultState(uint256 vaultId) external view returns (VaultInfo memory) {
        return vaults[vaultId];
    }

    function bCropBalanceOf(uint256 vaultId, address investor) external view returns (uint256) {
        return bCropBalances[vaultId][investor];
    }

    function getInvestorsCount(uint256 vaultId) external view returns (uint256) {
        return _vaultInvestors[vaultId].length;
    }

    function getInvestorAt(uint256 vaultId, uint256 index) external view returns (address) {
        return _vaultInvestors[vaultId][index];
    }
}
