import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { network } from "hardhat";

describe("PawnAgreementEvidenceRegistry", async () => {
  const { viem } = await network.create();
  const [admin, registrar, stranger] = await viem.getWalletClients();
  const id = `0x${"11".repeat(32)}` as const;
  const document = `0x${"22".repeat(32)}` as const;
  const consent = `0x${"33".repeat(32)}` as const;

  async function deploy() {
    return viem.deployContract("PawnAgreementEvidenceRegistry", [admin.account.address, registrar.account.address]);
  }

  it("records immutable document and consent commitments with ordered revisions", async () => {
    const registry = await deploy();
    await registry.write.recordVersion([id, 1, document, consent], { account: registrar.account });
    await registry.write.recordVersion([id, 1, document, consent], { account: registrar.account });
    assert.equal(await registry.read.latestVersion([id]), 1);
    const first = await registry.read.commitmentOf([id, 1]);
    assert.equal(first.documentDigest, document);
    assert.equal(first.consentDigest, consent);
    await registry.write.recordVersion([id, 2, `0x${"44".repeat(32)}`, `0x${"55".repeat(32)}`], { account: registrar.account });
    assert.equal(await registry.read.latestVersion([id]), 2);
    assert.equal((await registry.read.commitmentOf([id, 1])).documentDigest, document);
  });

  it("rejects conflicting retries, skipped revisions and empty commitments", async () => {
    const registry = await deploy();
    await viem.assertions.revertWithCustomError(registry.write.recordVersion([id, 2, document, consent], { account: registrar.account }), registry, "InvalidVersion");
    await viem.assertions.revertWithCustomError(registry.write.recordVersion([id, 1, document, `0x${"00".repeat(32)}`], { account: registrar.account }), registry, "EmptyCommitment");
    await registry.write.recordVersion([id, 1, document, consent], { account: registrar.account });
    await viem.assertions.revertWithCustomError(registry.write.recordVersion([id, 1, `0x${"44".repeat(32)}`, consent], { account: registrar.account }), registry, "CommitmentConflict");
  });

  it("restricts registration and pause to authorized roles", async () => {
    const registry = await deploy();
    await viem.assertions.revertWithCustomError(registry.write.recordVersion([id, 1, document, consent], { account: stranger.account }), registry, "AccessControlUnauthorizedAccount");
    await registry.write.pause({ account: admin.account });
    await viem.assertions.revertWithCustomError(registry.write.recordVersion([id, 1, document, consent], { account: registrar.account }), registry, "EnforcedPause");
  });
});
