/**
 * deploy-oracle.js
 * Redeploya SOLO el MockOracle (ahora unificado con Chainlink Functions).
 * Útil cuando cambias el contrato oracle sin tocar USDC, AgroNestCrop, etc.
 *
 * Uso:
 *   cd contracts
 *   pnpm install                  # asegúrate de tener @chainlink/contracts instalado
 *   npx hardhat run scripts/deploy-oracle.js --network sepolia
 *
 * Luego actualiza ORACLE_CONTRACT_ADDRESS en deployed_addresses.sepolia.json
 * y en tu .env si tienes la variable hardcodeada ahí.
 *
 * Para activar Chainlink Functions después del deploy:
 *   1. Ve a https://functions.chain.link y crea una suscripción en Sepolia
 *   2. Fondea con LINK de prueba: https://faucets.chain.link
 *   3. En Etherscan → contrato nuevo → Write → updateSubscriptionId(tuSubId)
 *      (o repite el deploy con _subId distinto de 0)
 *   4. En functions.chain.link → tu suscripción → "Add consumer" → address del contrato
 */

const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await ethers.getSigners();
  const networkName = network.name;

  console.log("=".repeat(60));
  console.log("Redeploy: MockOracle (Chainlink Functions unificado)");
  console.log("=".repeat(60));
  console.log(`Red      : ${networkName}`);
  console.log(`Deployer : ${deployer.address}`);
  console.log(`Balance  : ${ethers.formatEther(await ethers.provider.getBalance(deployer.address))} ETH`);
  console.log("=".repeat(60));

  // Leer addresses anteriores para conservar las que no cambian
  const jsonFilename = networkName === "localhost"
    ? "deployed_addresses.json"
    : `deployed_addresses.${networkName}.json`;
  const jsonPath = path.join(__dirname, "..", jsonFilename);

  let existing = {};
  if (fs.existsSync(jsonPath)) {
    existing = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
    console.log(`\nAddresses anteriores cargadas desde ${jsonFilename}`);
    console.log(`  Oracle viejo : ${existing.ORACLE_CONTRACT_ADDRESS ?? "(no registrado)"}`);
  }

  // Desplegar MockOracle unificado
  // _subId = 0 → modo mock, sin Chainlink. Llama updateSubscriptionId() para activarlo.
  console.log("\nDesplegando nuevo MockOracle...");
  const MockOracle = await ethers.getContractFactory("MockOracle");
  const oracle = await MockOracle.deploy(deployer.address, 0);
  await oracle.waitForDeployment();
  const oracleAddress = await oracle.getAddress();
  console.log(`  ✔ MockOracle nuevo : ${oracleAddress}`);

  // Actualizar solo ORACLE_CONTRACT_ADDRESS, mantener el resto
  const updated = {
    ...existing,
    ORACLE_CONTRACT_ADDRESS: oracleAddress,
    DEPLOYED_AT: new Date().toISOString(),
  };

  fs.writeFileSync(jsonPath, JSON.stringify(updated, null, 2));
  console.log(`\n✔ ${jsonFilename} actualizado con nueva address del oracle.`);

  if (networkName === "sepolia") {
    console.log(`\n🔍 Verifica en Etherscan:`);
    console.log(`   https://sepolia.etherscan.io/address/${oracleAddress}`);
    console.log(`\n📋 Próximos pasos para activar Chainlink Functions:`);
    console.log(`   1. https://functions.chain.link → Crear suscripción en Sepolia`);
    console.log(`   2. https://faucets.chain.link → Obtener LINK de prueba`);
    console.log(`   3. Fondear suscripción con 5 LINK`);
    console.log(`   4. "Add consumer" → ${oracleAddress}`);
    console.log(`   5. Llamar updateSubscriptionId(<tuSubId>) en Etherscan → Write`);
    console.log(`      O redeploya con: MockOracle.deploy(deployer.address, tuSubId)`);
    console.log(`\n⚠  Reinicia el backend para que cargue la nueva address del oracle.`);
  }
}

main()
  .then(() => process.exit(0))
  .catch((err) => { console.error(err); process.exit(1); });
