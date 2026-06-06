// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {FunctionsClient} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/FunctionsClient.sol";
import {FunctionsRequest} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/libraries/FunctionsRequest.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IVaultSettlement {
    function liquidate() external;
    function triggerDefault() external;
}

// MockOracle — Oráculo de ciclo de vida agrícola con Chainlink Functions opcional
//
// Modos de operación (un solo contrato, un solo deploy):
//  A) Mock manual: Deploy con _subId = 0. Admin llama advanceState() para todos los estados.
//  B) Chainlink Functions: Deploy con _subId = <subscriptionId de functions.chain.link>.
//     Los nodos consultan Open-Meteo; si <5 mm/7dias = sequia -> DEFAULT (~30s automatico).
//
// Router Chainlink Functions Sepolia: 0xb83E47C2bC239B3bf370bc41e1459A34b41238D0
contract MockOracle is FunctionsClient, Ownable {
    using FunctionsRequest for FunctionsRequest.Request;

    // ── Chainlink Functions — Sepolia ─────────────────────────────────
    address private constant FUNCTIONS_ROUTER = 0xb83E47C2bC239B3bf370bc41e1459A34b41238D0;
    bytes32 private constant DON_ID           = 0x66756e2d657468657265756d2d7365706f6c69612d3100000000000000000000;
    uint32  private constant GAS_LIMIT        = 300_000;

    // ── Estado del ciclo de vida ──────────────────────────────────────
    enum CropState {
        PLANTED,    // 0 — NFT minteado, bóveda no abierta
        ACTIVE,     // 1 — bóveda abierta, recaudando fondos
        MATURE,     // 2 — cosecha lista para liquidar o default
        LIQUIDATED, // 3 — venta exitosa, inversores cobran rendimiento
        DEFAULTED   // 4 — pérdida (sequía u otro), inversores recuperan reserva
    }

    mapping(address => CropState) public vaultStates;

    // ── Chainlink Functions ───────────────────────────────────────────
    uint64 public subscriptionId;
    mapping(bytes32 => address) public requestToVault;

    // ── Eventos ───────────────────────────────────────────────────────
    event StateAdvanced(address indexed vault, CropState newState);
    event WeatherRequested(address indexed vault, bytes32 indexed requestId);
    event WeatherFulfilled(address indexed vault, bool drought);

    // ── JavaScript ejecutado por los nodos Chainlink (Open-Meteo) ────
    // Suma precipitación de los últimos 7 días en la zona indicada.
    // Retorna 1 si hubo sequía (< 5 mm) → DEFAULTED, 0 si hubo lluvia → LIQUIDATED.
    // Para forzar sequía en demo: cambiar "total < 5" por "total < 9999".
    string private constant JS_SOURCE =
        "const lat = args[0];"
        "const lon = args[1];"
        "const url = 'https://api.open-meteo.com/v1/forecast'"
        "  + '?latitude=' + lat + '&longitude=' + lon"
        "  + '&daily=precipitation_sum&past_days=7&forecast_days=0&timezone=auto';"
        "const r = await Functions.makeHttpRequest({ url });"
        "if (r.error) throw Error('open-meteo: ' + JSON.stringify(r.error));"
        "const vals = r.data.daily.precipitation_sum || [];"
        "const total = vals.reduce((a, b) => a + (b || 0), 0);"
        "return Functions.encodeUint256(total < 5 ? 1 : 0);";

    // ─────────────────────────────────────────────────────────────────

    constructor(address initialOwner, uint64 _subId)
        FunctionsClient(FUNCTIONS_ROUTER)
        Ownable(initialOwner)
    {
        subscriptionId = _subId;
    }

    // ── Avance manual (todos los estados, incluyendo fallback MATURE) ─
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

    // ── Resolución automática vía Chainlink Functions ─────────────────
    function requestWeatherData(
        address vault,
        string calldata lat,
        string calldata lon
    ) external onlyOwner returns (bytes32 requestId) {
        require(subscriptionId != 0, "Oracle: Chainlink no configurado (subscriptionId = 0)");
        require(vaultStates[vault] == CropState.MATURE, "Oracle: vault debe estar en estado MATURE");

        FunctionsRequest.Request memory req;
        req.initializeRequestForInlineJavaScript(JS_SOURCE);
        string[] memory args = new string[](2);
        args[0] = lat;
        args[1] = lon;
        req.setArgs(args);

        requestId = _sendRequest(req.encodeCBOR(), subscriptionId, GAS_LIMIT, DON_ID);
        requestToVault[requestId] = vault;
        emit WeatherRequested(vault, requestId);
    }

    // ── Callback invocado por el router de Chainlink (~30s después) ───
    function fulfillRequest(
        bytes32 requestId,
        bytes memory response,
        bytes memory /* err */
    ) internal override {
        address vault = requestToVault[requestId];
        require(vault != address(0), "Oracle: requestId desconocido");

        uint256 droughtFlag = abi.decode(response, (uint256));
        bool drought = (droughtFlag == 1);

        if (drought) {
            vaultStates[vault] = CropState.DEFAULTED;
            IVaultSettlement(vault).triggerDefault();
        } else {
            vaultStates[vault] = CropState.LIQUIDATED;
            IVaultSettlement(vault).liquidate();
        }

        emit WeatherFulfilled(vault, drought);
        emit StateAdvanced(vault, vaultStates[vault]);
    }

    // ── Vistas y utilitarios ──────────────────────────────────────────
    function getState(address vault) external view returns (CropState) {
        return vaultStates[vault];
    }

    function registerVault(address vault) external onlyOwner {
        vaultStates[vault] = CropState.PLANTED;
    }

    function updateSubscriptionId(uint64 _subId) external onlyOwner {
        subscriptionId = _subId;
    }
}
