// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title bCROPToken - ERC-20 que representa la participación fraccionada de un inversor en una bóveda
/// @dev Solo el CropVault asociado puede mintear y quemar tokens.
contract bCROPToken is ERC20, Ownable {
    address public vault;

    event TokensMinted(address indexed to, uint256 amount);
    event TokensBurned(address indexed from, uint256 amount);

    modifier onlyVault() {
        require(msg.sender == vault, "bCROPToken: caller is not the vault");
        _;
    }

    constructor(address initialOwner, address _vault)
        ERC20("bCROP Token", "bCROP")
        Ownable(initialOwner)
    {
        vault = _vault;
    }

    /// @notice Acuña bCROP al inversor cuando deposita USDC
    function mint(address to, uint256 amount) external onlyVault {
        _mint(to, amount);
        emit TokensMinted(to, amount);
    }

    /// @notice Quema bCROP del inversor cuando reclama su retorno
    function burn(address from, uint256 amount) external onlyVault {
        _burn(from, amount);
        emit TokensBurned(from, amount);
    }

    /// @notice Permite actualizar la dirección del vault (ej: upgrade)
    function setVault(address _vault) external onlyOwner {
        vault = _vault;
    }

    /// @notice bCROP usa 6 decimales, igual que USDC, para ratio 1:1
    function decimals() public pure override returns (uint8) {
        return 6;
    }
}
