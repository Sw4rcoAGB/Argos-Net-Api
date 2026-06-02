// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./bCROPToken.sol";
import "./MockOracle.sol";

/// @title CropVault - Bóveda DeFi para financiamiento de cosechas
/// @dev Bloquea el NFT como colateral, acepta depósitos USDC, emite bCROP y gestiona liquidación.
///      Un vault por cosecha. El API wallet es el único caller externo (owner).
contract CropVault is Ownable, ReentrancyGuard {

    enum VaultStatus {
        OPEN,       // 0 - Recibiendo depósitos de USDC
        FUNDED,     // 1 - Meta alcanzada, fondos liberados al agricultor
        ACTIVE,     // 2 - Cultivo en curso (transitorio, gestionado por oráculo)
        LIQUIDATED, // 3 - Cosecha completada, inversores pueden reclamar + rendimiento
        DEFAULTED   // 4 - Pérdida de cosecha, inversores recuperan reserva proporcional
    }

    struct VaultConfig {
        uint256 cropTokenId;         // ID del NFT bloqueado como colateral
        uint256 fundingGoal;         // Meta total en USDC (6 decimales)
        uint256 fundingDeadline;     // Timestamp límite para recaudar
        uint256 reservePercent;      // % del fondeo reservado como seguro (ej: 5)
        uint256 yieldPercent;        // % de rendimiento prometido al inversor (ej: 12)
        uint256 totalRaised;         // Total USDC recaudado hasta ahora
        VaultStatus status;
    }

    IERC20      public immutable usdc;
    IERC721     public immutable cropNFT;
    MockOracle  public immutable oracle;
    bCROPToken  public bCrop;

    VaultConfig public config;
    address     public farmerAddress; // Agricultor que recibe los fondos liberados

    mapping(address => uint256) public investments; // inversor → USDC depositado
    address[] public investors;

    event VaultOpened(uint256 indexed cropTokenId, uint256 fundingGoal, uint256 deadline);
    event InvestmentReceived(address indexed investor, uint256 usdcAmount, uint256 bCropMinted);
    event FundingComplete(uint256 totalRaised, uint256 reserveAmount, uint256 disbursedToFarmer);
    event CropLiquidated(uint256 totalPayout, uint256 yieldAmount);
    event CropDefaulted(uint256 reserveAvailable);
    event ReturnsClaimed(address indexed investor, uint256 usdcAmount);

    modifier onlyOracle() {
        require(msg.sender == address(oracle), "CropVault: caller is not the oracle");
        _;
    }

    modifier inStatus(VaultStatus expected) {
        require(config.status == expected, "CropVault: invalid vault status for this action");
        _;
    }

    constructor(
        address _owner,
        address _usdc,
        address _cropNFT,
        address _oracle
    ) Ownable(_owner) {
        usdc    = IERC20(_usdc);
        cropNFT = IERC721(_cropNFT);
        oracle  = MockOracle(_oracle);
    }

    /// @notice Abre la ronda de financiamiento. Transfiere el NFT al vault como colateral.
    /// @dev El API wallet debe haber aprobado el vault para transferir el NFT antes de llamar esto.
    function openRound(
        uint256 cropTokenId,
        uint256 fundingGoal,
        uint256 fundingDeadline,
        uint256 reservePercent,
        uint256 yieldPercent,
        address bCropAddress,
        address farmer
    ) external onlyOwner {
        require(config.fundingGoal == 0, "CropVault: round already opened");
        require(reservePercent <= 30, "CropVault: reserve too high");
        require(yieldPercent <= 100, "CropVault: yield too high");

        cropNFT.transferFrom(msg.sender, address(this), cropTokenId);
        bCrop         = bCROPToken(bCropAddress);
        farmerAddress = farmer;

        config = VaultConfig({
            cropTokenId:     cropTokenId,
            fundingGoal:     fundingGoal,
            fundingDeadline: fundingDeadline,
            reservePercent:  reservePercent,
            yieldPercent:    yieldPercent,
            totalRaised:     0,
            status:          VaultStatus.OPEN
        });

        emit VaultOpened(cropTokenId, fundingGoal, fundingDeadline);
    }

    /// @notice El API wallet deposita USDC en nombre de un inversor y le mintea bCROP.
    /// @dev El API wallet debe haber aprobado el vault para gastar USDC antes de llamar esto.
    function deposit(uint256 usdcAmount, address investor)
        external
        nonReentrant
        onlyOwner
        inStatus(VaultStatus.OPEN)
    {
        require(block.timestamp <= config.fundingDeadline, "CropVault: funding deadline passed");
        require(usdcAmount > 0, "CropVault: amount must be greater than zero");
        require(
            config.totalRaised + usdcAmount <= config.fundingGoal,
            "CropVault: exceeds funding goal"
        );

        usdc.transferFrom(msg.sender, address(this), usdcAmount);
        bCrop.mint(investor, usdcAmount); // ratio 1:1 USDC:bCROP

        if (investments[investor] == 0) {
            investors.push(investor);
        }
        investments[investor] += usdcAmount;
        config.totalRaised    += usdcAmount;

        emit InvestmentReceived(investor, usdcAmount, usdcAmount);

        if (config.totalRaised == config.fundingGoal) {
            _completeFunding();
        }
    }

    function _completeFunding() internal {
        config.status = VaultStatus.FUNDED;
        uint256 reserve   = (config.totalRaised * config.reservePercent) / 100;
        uint256 disbursed = config.totalRaised - reserve;
        // Libera fondos menos la reserva al agricultor
        usdc.transfer(farmerAddress, disbursed);
        emit FundingComplete(config.totalRaised, reserve, disbursed);
    }

    /// @notice Llamado por el oráculo cuando la cosecha se completó exitosamente.
    ///         El API wallet debe pre-fondear el vault con el yield antes de llamar esto.
    function liquidate() external onlyOracle inStatus(VaultStatus.FUNDED) {
        config.status = VaultStatus.LIQUIDATED;
        uint256 yieldTotal = (config.totalRaised * config.yieldPercent) / 100;
        emit CropLiquidated(config.totalRaised, yieldTotal);
    }

    /// @notice Llamado por el oráculo cuando la cosecha fracasó (default).
    function triggerDefault() external onlyOracle inStatus(VaultStatus.FUNDED) {
        config.status = VaultStatus.DEFAULTED;
        uint256 reserve = (config.totalRaised * config.reservePercent) / 100;
        emit CropDefaulted(reserve);
    }

    /// @notice El API wallet reclama el retorno en nombre de un inversor y le transfiere USDC.
    /// @dev El inversor debe haber aprobado el vault para quemar sus bCROP, o el API los transfiere.
    function claimReturns(address investor)
        external
        nonReentrant
        onlyOwner
    {
        require(
            config.status == VaultStatus.LIQUIDATED || config.status == VaultStatus.DEFAULTED,
            "CropVault: vault not in claimable state"
        );

        uint256 bCropBalance = bCrop.balanceOf(investor);
        require(bCropBalance > 0, "CropVault: investor has no bCROP to redeem");

        uint256 payout;
        if (config.status == VaultStatus.LIQUIDATED) {
            // Principal + rendimiento proporcional
            uint256 yieldPerToken = (config.yieldPercent * 1e6) / 100;
            payout = bCropBalance + (bCropBalance * yieldPerToken / 1e6);
        } else {
            // DEFAULTED: solo reserva proporcional según participación
            uint256 reserve = (config.totalRaised * config.reservePercent) / 100;
            payout = (bCropBalance * reserve) / config.totalRaised;
        }

        bCrop.burn(investor, bCropBalance);
        usdc.transfer(investor, payout);

        emit ReturnsClaimed(investor, payout);
    }

    // ─── Vistas ────────────────────────────────────────────────────────────────

    function getVaultState() external view returns (VaultConfig memory) {
        return config;
    }

    function getInvestorBalance(address investor)
        external
        view
        returns (uint256 invested, uint256 bCropHeld)
    {
        invested  = investments[investor];
        bCropHeld = bCrop.balanceOf(investor);
    }

    function getInvestorsCount() external view returns (uint256) {
        return investors.length;
    }

    function getInvestorAt(uint256 index) external view returns (address) {
        return investors[index];
    }
}
