import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { network } from "hardhat";

describe("CollateralProofRegistry", async () => {
  const { viem } = await network.create();
  const [admin, registrar, stranger] = await viem.getWalletClients();
  const eventId = `0x${"11".repeat(32)}` as const;
  const digest = `0x${"22".repeat(32)}` as const;

  async function deploy() {
    return viem.deployContract("CollateralProofRegistry", [admin.account.address, registrar.account.address]);
  }

  it("registers one opaque commitment and accepts an identical retry", async () => {
    const registry = await deploy();
    await registry.write.registerProof([eventId, digest], { account: registrar.account });
    await registry.write.registerProof([eventId, digest], { account: registrar.account });
    assert.equal(await registry.read.proofOf([eventId]), digest);
  });

  it("rejects a different digest for the same event", async () => {
    const registry = await deploy();
    await registry.write.registerProof([eventId, digest], { account: registrar.account });
    await viem.assertions.revertWithCustomError(
      registry.write.registerProof([eventId, `0x${"33".repeat(32)}`], { account: registrar.account }),
      registry,
      "ProofConflict",
    );
  });

  it("enforces registrar role and admin pause", async () => {
    const registry = await deploy();
    await viem.assertions.revertWithCustomError(registry.write.registerProof([eventId, digest], { account: stranger.account }), registry, "AccessControlUnauthorizedAccount");
    await registry.write.pause({ account: admin.account });
    await viem.assertions.revertWithCustomError(registry.write.registerProof([eventId, digest], { account: registrar.account }), registry, "EnforcedPause");
    await registry.write.unpause({ account: admin.account });
    await registry.write.registerProof([eventId, digest], { account: registrar.account });
    assert.equal(await registry.read.proofOf([eventId]), digest);
  });
});
