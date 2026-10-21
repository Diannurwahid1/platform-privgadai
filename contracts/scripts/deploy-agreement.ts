import { network } from "hardhat";

const { viem } = await network.create({ network: "bscTestnet", chainType: "l1" });
const publicClient = await viem.getPublicClient();
if (await publicClient.getChainId() !== 97) throw new Error("Refusing deployment outside BSC Testnet");
const [deployer] = await viem.getWalletClients();
const balance = await publicClient.getBalance({ address: deployer.account.address });
console.log(`Deployer: ${deployer.account.address}; balance: ${balance} wei`);
if (balance === 0n) throw new Error("Fund the deployer with testnet tBNB first");
const registry = await viem.deployContract("PawnAgreementEvidenceRegistry", [deployer.account.address, deployer.account.address]);
const code = await publicClient.getBytecode({ address: registry.address });
if (!code || code === "0x") throw new Error("Deployment receipt has no bytecode");
console.log(`PawnAgreementEvidenceRegistry: ${registry.address}`);
console.log(`Explorer: https://testnet.bscscan.com/address/${registry.address}`);
