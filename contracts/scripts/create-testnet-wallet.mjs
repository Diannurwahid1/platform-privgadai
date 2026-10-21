import { randomBytes } from "node:crypto";
import { writeFileSync } from "node:fs";
import { privateKeyToAccount } from "viem/accounts";

const key = `0x${randomBytes(32).toString("hex")}`;
const account = privateKeyToAccount(key);
writeFileSync(new URL("../.env", import.meta.url), `BSC_TESTNET_PRIVATE_KEY=${key}\n`, { flag: "wx", mode: 0o600 });
console.log(account.address);
