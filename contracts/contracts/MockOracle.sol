// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

interface IVaultSettlement {
    function liquidate() external;
    function triggerDefault() external;
}

/// @title MockOracle - Oráculo simulado de ciclo de vida agrícola para el hackathon
/// @dev El API wallet (owner) avanza los estados manualmente para la demo.
///      En producción, esto se reemplazaría por Chainlink Functions o similar.
contract MockOracle is Ownable {
    enum CropState {
        PLANTED,    // 0 - NFT minteado, bóveda no abierta aún
        ACTIVE,     // 1 - Bóveda abierta y recaudando fondos
        MATURE,     // 2 - Cultivo maduro, listo para liquidar o default
        LIQUIDATED, // 3 - Cosecha vendida, inversores cobran con rendimiento
        DEFAULTED   // 4 - Pérdida de cosecha, inversores recuperan solo la reserva
    }

    mapping(address => CropState) public vaultStates;

    event StateAdvanced(address indexed vault, CropState newState);

    constructor(address initialOwner) Ownable(initialOwner) {}

    /// @notice Avanza el estado del ciclo de vida de una bóveda.
    /// @param vault Dirección del contrato CropVault
    /// @param success Si es true y el estado es MATURE → LIQUIDATED; si es false → DEFAULTED
    function advanceState(address vault, bool success) external onlyOwner {
        CropState current = vaultStates[vault];
        require(
            current != CropState.LIQUIDATED && current != CropState.DEFAULTED,
            "Oracle: vault is in a terminal state"
        );

        CropState newState;

        if (current == CropState.MATURE) {
            if (success) {
                newState = CropState.LIQUIDATED;
                IVaultSettlement(vault).liquidate();
            } else {
                newState = CropState.DEFAULTED;
                IVaultSettlement(vault).triggerDefault();
            }
        } else {
            newState = CropState(uint8(current) + 1);
        }

        vaultStates[vault] = newState;
        emit StateAdvanced(vault, newState);
    }

    /// @notice Retorna el estado actual de una bóveda en el oráculo
    function getState(address vault) external view returns (CropState) {
        return vaultStates[vault];
    }

    /// @notice Inicializa el estado de una bóveda recién creada (llamado por el API al abrir la bóveda)
    function registerVault(address vault) external onlyOwner {
        require(vaultStates[vault] == CropState.PLANTED, "Oracle: vault already registered");
        // El estado inicial PLANTED ya es 0 por defecto del mapping,
        // este método permite avanzar a ACTIVE explícitamente al abrir la bóveda
        vaultStates[vault] = CropState.PLANTED;
    }
}
