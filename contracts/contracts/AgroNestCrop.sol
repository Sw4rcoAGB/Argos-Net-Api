// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title AgroNestCrop - ERC-721 que representa un contrato forward de cosecha
/// @dev Un NFT = una cosecha física única. Solo el API wallet (owner) puede mintear.
contract AgroNestCrop is ERC721, Ownable {
    uint256 private _nextTokenId;

    struct CropMetadata {
        string  farmId;           // UUID que vincula con el row Cosecha en Postgres
        uint256 hectares;         // escalado x100 (ej: 150 = 1.50 ha)
        string  grainType;        // "maiz", "trigo", "soya", etc.
        uint256 estimatedYieldKg; // rendimiento estimado en kg
        uint256 capitalRequired;  // capital requerido en USDC (6 decimales)
        uint256 harvestDate;      // unix timestamp de la cosecha estimada
        address farmer;           // dirección del API wallet (custodio)
    }

    mapping(uint256 => CropMetadata) public cropData;

    event CropMinted(
        uint256 indexed tokenId,
        address indexed farmer,
        string  farmId,
        uint256 capitalRequired,
        uint256 harvestDate
    );

    constructor(address initialOwner)
        ERC721("AgroNestCrop", "ACROP")
        Ownable(initialOwner)
    {}

    /// @notice Mintea un nuevo NFT de cosecha. Solo puede llamarlo el API wallet.
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

    /// @notice Retorna los metadatos de una cosecha tokenizada
    function getCropData(uint256 tokenId)
        external
        view
        returns (CropMetadata memory)
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return cropData[tokenId];
    }

    /// @notice Retorna el total de NFTs minteados
    function totalSupply() external view returns (uint256) {
        return _nextTokenId;
    }
}
