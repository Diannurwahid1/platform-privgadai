import { network } from "hardhat";
import { keccak256, stringToHex } from "viem";

const address = process.env.AGREEMENT_REGISTRY_ADDRESS as `0x${string}` | undefined;
if (!address) throw new Error("Set AGREEMENT_REGISTRY_ADDRESS");
const { viem } = await network.create({ network: "bscTestnet", chainType: "l1" });
const client = await viem.getPublicClient();
if (await client.getChainId() !== 97) throw new Error("Refusing smoke test outside BSC Testnet");
const [registrar] = await viem.getWalletClients();
const registry = await viem.getContractAt("PawnAgreementEvidenceRegistry", address);

// Synthetic, non-customer data; safe to expose on a public test network.
const agreementId = keccak256(stringToHex("privgadai.synthetic.agreement.v1"));
const documentDigest = keccak256(stringToHex("synthetic.sbg.document.v1"));
const consentDigest = keccak256(stringToHex("synthetic.borrower.consent.v1"));
const txHash = await registry.write.recordVersion(
  [agreementId, 1, documentDigest, consentDigest],
  { account: registrar.account },
);
const receipt = await client.waitForTransactionReceipt({ hash: txHash });
if (receipt.status !== "success") throw new Error("Agreement registration reverted");
const commitment = await registry.read.commitmentOf([agreementId, 1]);
if (commitment.documentDigest !== documentDigest || commitment.consentDigest !== consentDigest) {
  throw new Error("On-chain agreement commitment mismatch");
}
console.log(`Transaction: ${txHash}`);
console.log(`Block: ${receipt.blockNumber}`);
console.log(`Agreement version: ${await registry.read.latestVersion([agreementId])}`);
console.log("Document and consent commitments match on-chain: true");
