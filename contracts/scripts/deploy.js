const { ethers, network } = require("hardhat");
const fs   = require("fs");
const path = require("path");

// Chain IDs conocidos
const CHAIN_IDS = {
  hardhat:   1337,
  localhost: 1337,
  sepolia:   11155111,
  mainnet:   1,
  polygon:   137,
};

async function main() {
  const [deployer] = await ethers.getSigners();
  const networkName = network.name;
  const chainId     = CHAIN_IDS[networkName] ?? (await ethers.provider.getNetwork()).chainId;

  console.log("=".repeat(50));
  console.log(`Red       : ${networkName} (chainId: ${chainId})`);
  console.log(`Deployer  : ${deployer.address}`);
  console.log(`Balance   : ${ethers.formatEther(await ethers.provider.getBalance(deployer.address))} ETH`);
  console.log("=".repeat(50));

  if (Number(ethers.formatEther(await ethers.provider.getBalance(deployer.address))) < 0.01 && networkName !== "hardhat") {
    console.warn("\n⚠  ADVERTENCIA: El balance es muy bajo. Asegúrate de tener ETH suficiente para el deploy.");
  }

  // ── 1. MockUSDC ──────────────────────────────────────────────────────────
  console.log("\nDesplegando MockUSDC...");
  const MockUSDC = await ethers.getContractFactory("MockUSDC");
  const usdc = await MockUSDC.deploy(deployer.address);
  await usdc.waitForDeployment();
  const usdcAddress = await usdc.getAddress();
  console.log("  ✔ MockUSDC         :", usdcAddress);

  // ── 2. MockOracle ─────────────────────────────────────────────────────────
  console.log("Desplegando MockOracle...");
  const MockOracle = await ethers.getContractFactory("MockOracle");
  const oracle = await MockOracle.deploy(deployer.address);
  await oracle.waitForDeployment();
  const oracleAddress = await oracle.getAddress();
  console.log("  ✔ MockOracle       :", oracleAddress);

  // ── 3. AgroNestCrop (ERC-721) ─────────────────────────────────────────────
  console.log("Desplegando AgroNestCrop...");
  const AgroNestCrop = await ethers.getContractFactory("AgroNestCrop");
  const cropNFT = await AgroNestCrop.deploy(deployer.address);
  await cropNFT.waitForDeployment();
  const cropNFTAddress = await cropNFT.getAddress();
  console.log("  ✔ AgroNestCrop     :", cropNFTAddress);

  // Nota: bCROPToken y CropVault se despliegan por cosecha (uno por cada NFT)
  // El script de deploy solo crea los contratos base/singleton.

  const addresses = {
    USDC_CONTRACT_ADDRESS:   usdcAddress,
    ORACLE_CONTRACT_ADDRESS: oracleAddress,
    CROP_CONTRACT_ADDRESS:   cropNFTAddress,
    DEPLOYER_ADDRESS:        deployer.address,
    CHAIN_ID:                chainId,
    NETWORK:                 networkName,
    DEPLOYED_AT:             new Date().toISOString(),
  };

  // ── Guardar JSON con las addresses ────────────────────────────────────────
  // Local: deployed_addresses.json (git-ignorado, se regenera cada sesión)
  // Otras redes: deployed_addresses.<network>.json (puedes commitear)
  const jsonFilename = networkName === "localhost"
    ? "deployed_addresses.json"
    : `deployed_addresses.${networkName}.json`;

  const jsonPath = path.join(__dirname, "..", jsonFilename);
  fs.writeFileSync(jsonPath, JSON.stringify(addresses, null, 2));
  console.log(`\n✔ Addresses guardadas en: ${jsonPath}`);

  // ── Resumen final ─────────────────────────────────────────────────────────
  console.log("\n" + "=".repeat(50));
  console.log("DEPLOY COMPLETADO");
  console.log("=".repeat(50));

  if (networkName !== "localhost" && networkName !== "hardhat") {
    // Para redes reales: el script deploy-sepolia.ps1 actualiza .env automáticamente.
    // Si lo corriste manualmente, usa estas líneas:
    console.log(`\n📋 Copia estas líneas en tu .env (o ejecuta deploy-sepolia.ps1 para hacerlo automático):\n`);
    console.log(`RPC_URL=<tu URL de Alchemy/Infura para ${networkName}>`);
    console.log(`CHAIN_ID=${chainId}`);
    console.log(`USDC_CONTRACT_ADDRESS=${usdcAddress}`);
    console.log(`ORACLE_CONTRACT_ADDRESS=${oracleAddress}`);
    console.log(`CROP_CONTRACT_ADDRESS=${cropNFTAddress}`);

    if (networkName === "sepolia") {
      console.log(`\n🔍 Verifica los contratos en Etherscan:`);
      console.log(`   MockUSDC   : https://sepolia.etherscan.io/address/${usdcAddress}`);
      console.log(`   MockOracle : https://sepolia.etherscan.io/address/${oracleAddress}`);
      console.log(`   AgroNestCrop: https://sepolia.etherscan.io/address/${cropNFTAddress}`);
    }
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
