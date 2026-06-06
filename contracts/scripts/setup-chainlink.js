/**
 * setup-chainlink.js
 * Configura Chainlink Functions para el MockOracle en Sepolia:
 *   1. Verifica balance de LINK
 *   2. Crea suscripción en el Functions Router
 *   3. Fondea con LINK via transferAndCall (ERC-677)
 *   4. Agrega MockOracle como consumer
 *   5. Llama updateSubscriptionId en el contrato
 *
 * Uso:
 *   cd contracts
 *   npx hardhat run scripts/setup-chainlink.js --network sepolia
 *
 * Requisitos:
 *   - Wallet con ETH para gas (~0.003 ETH para 3 transacciones)
 *   - Wallet con LINK de prueba (mínimo 3 LINK)
 *     Obtén LINK gratis en: https://faucets.chain.link (Sepolia → 25 LINK)
 */

const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

// ── Direcciones Chainlink en Sepolia ──────────────────────────────────────────
const FUNCTIONS_ROUTER = "0xb83E47C2bC239B3bf370bc41e1459A34b41238D0";
const LINK_TOKEN       = "0x779877A7B0D9E8603169DdbD7836e478b4624789";
const LINK_FUND_AMOUNT = ethers.parseEther("3"); // 3 LINK mínimo recomendado

// ── ABIs mínimos ──────────────────────────────────────────────────────────────
const ROUTER_ABI = [
  "event SubscriptionCreated(uint64 indexed subscriptionId, address owner)",
  "function createSubscription() external returns (uint64)",
  "function addConsumer(uint64 subscriptionId, address consumer) external",
  "function getSubscription(uint64 subscriptionId) external view returns (uint96 balance, uint96 blockedBalance, address owner, address[] memory consumers)",
];

const LINK_ABI = [
  "function balanceOf(address account) external view returns (uint256)",
  "function transferAndCall(address to, uint256 value, bytes calldata data) external returns (bool)",
];

const ORACLE_ABI = [
  "function updateSubscriptionId(uint64 _subId) external",
  "function subscriptionId() external view returns (uint64)",
];

// ─────────────────────────────────────────────────────────────────────────────

async function main() {
  const [deployer] = await ethers.getSigners();
  const networkName = network.name;

  if (networkName !== "sepolia") {
    throw new Error(`Este script solo funciona en sepolia, no en '${networkName}'`);
  }

  // Leer addresses del archivo de deploy
  const jsonPath = path.join(__dirname, "..", "deployed_addresses.sepolia.json");
  if (!fs.existsSync(jsonPath)) {
    throw new Error(`No se encontró deployed_addresses.sepolia.json — despliega primero el oracle`);
  }
  const addresses = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
  const oracleAddress = addresses.ORACLE_CONTRACT_ADDRESS;
  if (!oracleAddress) {
    throw new Error("ORACLE_CONTRACT_ADDRESS no está en deployed_addresses.sepolia.json");
  }

  console.log("=".repeat(60));
  console.log("Setup: Chainlink Functions para MockOracle");
  console.log("=".repeat(60));
  console.log(`Deployer : ${deployer.address}`);
  console.log(`Oracle   : ${oracleAddress}`);
  console.log(`ETH      : ${ethers.formatEther(await ethers.provider.getBalance(deployer.address))} ETH`);
  console.log("=".repeat(60));

  const router = new ethers.Contract(FUNCTIONS_ROUTER, ROUTER_ABI, deployer);
  const link   = new ethers.Contract(LINK_TOKEN, LINK_ABI, deployer);
  const oracle = new ethers.Contract(oracleAddress, ORACLE_ABI, deployer);

  // ── Verificar balance LINK ────────────────────────────────────────────────
  const linkBalance = await link.balanceOf(deployer.address);
  console.log(`\nBalance LINK : ${ethers.formatEther(linkBalance)} LINK`);
  console.log(`Requerido    : ${ethers.formatEther(LINK_FUND_AMOUNT)} LINK`);

  if (linkBalance < LINK_FUND_AMOUNT) {
    console.log("\n⚠  LINK insuficiente para continuar.");
    console.log("   1. Ve a https://faucets.chain.link");
    console.log("   2. Selecciona Ethereum Sepolia");
    console.log("   3. Pide LINK (recibirás 25 LINK)");
    console.log(`   4. Usa esta wallet: ${deployer.address}`);
    console.log("   5. Vuelve a ejecutar este script cuando tengas LINK");
    process.exit(1);
  }

  // ── Verificar si ya tiene subscriptionId ─────────────────────────────────
  const currentSubId = await oracle.subscriptionId();
  if (currentSubId > 0n) {
    console.log(`\n✅ El oracle ya tiene subscriptionId = ${currentSubId}`);
    try {
      const sub = await router.getSubscription(currentSubId);
      console.log(`   Balance suscripción : ${ethers.formatEther(sub.balance)} LINK`);
      console.log(`   Consumers           : ${sub.consumers.join(", ")}`);
      console.log("\nChainlink Functions ya estaba configurado. Sin cambios.");
    } catch {
      console.log("   (no se pudo consultar la suscripción — puede haber expirado)");
    }
    process.exit(0);
  }

  // ── Paso 1: Crear suscripción ─────────────────────────────────────────────
  console.log("\n[1/4] Creando suscripción en Chainlink Functions Router...");
  const createTx = await router.createSubscription();
  const createReceipt = await createTx.wait();

  // Extraer subscriptionId del evento SubscriptionCreated
  const subCreatedTopic = ethers.id("SubscriptionCreated(uint64,address)");
  const subLog = createReceipt.logs.find(l => l.topics[0] === subCreatedTopic);
  if (!subLog) {
    throw new Error("No se encontró el evento SubscriptionCreated en el receipt");
  }
  const subId = BigInt(subLog.topics[1]);
  console.log(`  ✔ Suscripción creada : ID = ${subId}`);
  console.log(`  tx: ${createTx.hash}`);

  // ── Paso 2: Fondear suscripción con LINK (ERC-677 transferAndCall) ────────
  console.log(`\n[2/4] Fondeando suscripción con ${ethers.formatEther(LINK_FUND_AMOUNT)} LINK...`);
  const fundData = ethers.AbiCoder.defaultAbiCoder().encode(["uint64"], [subId]);
  const fundTx   = await link.transferAndCall(FUNCTIONS_ROUTER, LINK_FUND_AMOUNT, fundData);
  await fundTx.wait();
  console.log(`  ✔ Suscripción fondeada`);
  console.log(`  tx: ${fundTx.hash}`);

  // ── Paso 3: Agregar oracle como consumer ──────────────────────────────────
  console.log(`\n[3/4] Agregando oracle como consumer...`);
  const addTx = await router.addConsumer(subId, oracleAddress);
  await addTx.wait();
  console.log(`  ✔ Consumer agregado : ${oracleAddress}`);
  console.log(`  tx: ${addTx.hash}`);

  // ── Paso 4: Actualizar subscriptionId en el contrato oracle ──────────────
  console.log(`\n[4/4] Actualizando subscriptionId en el contrato oracle...`);
  const updateTx = await oracle.updateSubscriptionId(subId);
  await updateTx.wait();
  console.log(`  ✔ Oracle actualizado con subscriptionId = ${subId}`);
  console.log(`  tx: ${updateTx.hash}`);

  // ── Verificación final ────────────────────────────────────────────────────
  const finalSubId = await oracle.subscriptionId();
  const sub        = await router.getSubscription(finalSubId);
  console.log(`\nVerificación:`);
  console.log(`  oracle.subscriptionId() = ${finalSubId} ✔`);
  console.log(`  Suscripción balance     = ${ethers.formatEther(sub.balance)} LINK`);
  console.log(`  Consumers               = ${sub.consumers.join(", ")}`);

  // ── Guardar en JSON ───────────────────────────────────────────────────────
  const updated = {
    ...addresses,
    CHAINLINK_SUBSCRIPTION_ID: subId.toString(),
    CHAINLINK_SETUP_AT: new Date().toISOString(),
  };
  fs.writeFileSync(jsonPath, JSON.stringify(updated, null, 2));
  console.log(`\n✔ deployed_addresses.sepolia.json actualizado`);

  // ── Resumen ───────────────────────────────────────────────────────────────
  console.log("\n" + "=".repeat(60));
  console.log("✅ Chainlink Functions ACTIVADO");
  console.log("=".repeat(60));
  console.log(`Suscripción ID : ${subId}`);
  console.log(`Oracle         : ${oracleAddress}`);
  console.log(`LINK fondeado  : ${ethers.formatEther(LINK_FUND_AMOUNT)} LINK`);
  console.log(`\nPara usar desde el backend:`);
  console.log(`  POST /oracle/avanzar-chainlink`);
  console.log(`  Body: { "cosecha_id": <id>, "lat": "19.4326", "lon": "-99.1332" }`);
  console.log(`  (la bóveda debe estar en estado MATURE)`);
  console.log(`\nVerifica en: https://functions.chain.link/sepolia/${subId}`);
}

main()
  .then(() => process.exit(0))
  .catch((err) => { console.error("\n❌ Error:", err.message || err); process.exit(1); });
