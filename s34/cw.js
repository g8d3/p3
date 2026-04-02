const { Wallet } = require("ethers");

// Configuration: Default RAW to true if not specified
const PASSWORD = process.env.WPWD;
const SHOW_RAW = process.env.RAW !== "false"; // Default is true
const SHOW_JSON = process.env.JSON === "true"; // Default is false

async function create() {
  const wallet = Wallet.createRandom();

  console.log(`Address:     ${wallet.address}`);

  if (SHOW_RAW) {
    console.log(`Mnemonic:    ${wallet.mnemonic.phrase}`);
    console.log(`Private Key: ${wallet.privateKey}`);
  }

  if (SHOW_JSON) {
    if (!PASSWORD) {
      console.error("\nError: JSON requested but WPWD (password) missing.");
      process.exit(1);
    }
    const encrypted = await wallet.encrypt(PASSWORD);
    console.log(`JSON: ${encrypted}`);
  }
}

create();