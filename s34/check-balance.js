const { JsonRpcProvider, formatEther, FetchRequest } = require("ethers");

async function checkBalance() {
  const address = process.env.WALLET_ADDRESS;
  const url = "https://ethereum-rpc.publicnode.com";

  try {
    // 1. We manually specify the network (Chain 1 = Mainnet)
    // This prevents the "detect network" background loop.
    const provider = new JsonRpcProvider(url, 1, {
      staticNetwork: true 
    });

    const balance = await provider.getBalance(address);

    console.log(`✅ Provider: ${url}`);
    console.log(`Address:  ${address}`);
    console.log(`Balance:  ${formatEther(balance)} ETH`);

    // Explicitly exit so background polling doesn't hang the terminal
    process.exit(0);
  } catch (error) {
    console.error("❌ Error:", error.message);
    process.exit(1);
  }
}

checkBalance();