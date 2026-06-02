// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title MockUSDC - ERC20 stablecoin simulado para desarrollo local
/// @dev Solo para entorno de desarrollo/hackathon. El owner es el API wallet.
contract MockUSDC is ERC20, Ownable {
    constructor(address initialOwner)
        ERC20("Mock USDC", "mUSDC")
        Ownable(initialOwner)
    {
        // Pre-mint 10M USDC al API wallet
        _mint(initialOwner, 10_000_000 * 10 ** 6);
    }

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    /// @notice Permite al owner acuñar tokens para cualquier dirección (faucet de desarrollo)
    function faucet(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
