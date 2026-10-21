import { randomBytes } from "node:crypto";
import { network } from "hardhat";

const address = process.env.PROOF_CONTRACT_ADDRESS as `0x${string}` | undefined;
if (!address) throw new Error("Set PROOF_CONTRACT_ADDRESS");
const { viem } = await network.create({ network: "bscTestnet", chainType: "l1" });
const publicClient = await viem.getPublicClient();
if (await publicClient.getChainId() !== 97) throw new Error("Wrong chain");
const [registrar] = await viem.getWalletClients();
const registry = await viem.getContractAt("CollateralProofRegistry", address);
const eventId = `0x${randomBytes(32).toString("hex")}` as const;
const digest = `0x${randomBytes(32).toString("hex")}` as const;
const tx = await registry.write.registerProof([eventId, digest], { account: registrar.account });
const receipt = await publicClient.waitForTransactionReceipt({ hash: tx });
if (receipt.status !== "success" || await registry.read.proofOf([eventId]) !== digest) throw new Error("Proof round trip failed");
console.log(`Synthetic test proof confirmed: ${tx}`);
console.log(`Block: ${receipt.blockNumber}`);
console.log(`Explorer: https://testnet.bscscan.com/tx/${tx}`);
