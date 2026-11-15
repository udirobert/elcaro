// Generates tests/fixtures/x402/*.json — signed x402 payment payloads.
// Uses viem (resolved from app/web's node_modules) so the fixtures are
// produced by the SAME library the Next.js route verifies with — a Python
// pass here proves parity with the reference implementation.
//
//   node tests/fixtures/x402/generate.mjs
//
// The key below is a fixture-only throwaway — it funds nothing. Do not
// send value to it.
import { createRequire } from "module";
import { writeFileSync, mkdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const require = createRequire(
  join(dirname(fileURLToPath(import.meta.url)), "../../../app/web/package.json")
);
const { privateKeyToAccount } = require("viem/accounts");

const PAYER_KEY =
  "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"; // devnet key #1, fixture-only
const PAYER = privateKeyToAccount(PAYER_KEY).address;
const PAYTO = "0x1e17B4FB12B29045b29475f74E536Db97Ddc5D40"; // matches prod offer
const AMOUNT = "10000"; // $0.01

const EIP3009_TYPES = {
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" },
  ],
};

// Mirrors NETWORKS in route.ts / core/x402.py.
const NETWORKS = {
  "eip155:8453": {
    chainId: 8453,
    asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    extra: { name: "USD Coin", version: "2" },
  },
  "eip155:84532": {
    chainId: 84532,
    asset: "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    extra: { name: "USDC", version: "2" },
  },
};

function offer(network) {
  const n = NETWORKS[network];
  return {
    scheme: "exact",
    network,
    asset: n.asset,
    amount: AMOUNT,
    payTo: PAYTO,
    maxTimeoutSeconds: 300,
    extra: n.extra,
  };
}

let nonceCounter = 1;
function nextNonce() {
  return "0x" + String(nonceCounter++).padStart(64, "0");
}

async function sign(network, auth) {
  const n = NETWORKS[network];
  const account = privateKeyToAccount(PAYER_KEY);
  const signature = await account.signTypedData({
    domain: {
      name: n.extra.name,
      version: n.extra.version,
      chainId: n.chainId,
      verifyingContract: n.asset,
    },
    types: EIP3009_TYPES,
    primaryType: "TransferWithAuthorization",
    message: {
      from: auth.from,
      to: auth.to,
      value: BigInt(auth.value),
      validAfter: BigInt(auth.validAfter),
      validBefore: BigInt(auth.validBefore),
      nonce: auth.nonce,
    },
  });
  return {
    x402Version: 2,
    scheme: "exact",
    network,
    accepted: offer(network),
    payload: { signature, authorization: auth },
  };
}

const FAR_FUTURE = "4102444800"; // 2100 — tests pin `now`, so fixtures never age out
const base = (over = {}) => ({
  from: PAYER,
  to: PAYTO,
  value: AMOUNT,
  validAfter: "0",
  validBefore: FAR_FUTURE,
  nonce: nextNonce(),
  ...over,
});

const out = join(dirname(fileURLToPath(import.meta.url)));
mkdirSync(out, { recursive: true });
const write = (name, obj) =>
  writeFileSync(join(out, name), JSON.stringify(obj, null, 2) + "\n");

write("payer.json", {
  note: "fixture-only keypair (hardhat devnet key #1) — funds nothing",
  payerKey: PAYER_KEY,
  payer: PAYER,
  payTo: PAYTO,
  amount: AMOUNT,
});
write("offers.json", Object.keys(NETWORKS).map(offer));

write("payment_valid_sepolia.json", await sign("eip155:84532", base()));
write("payment_valid_mainnet.json", await sign("eip155:8453", base()));
write(
  "payment_wrong_recipient.json",
  await sign("eip155:84532", base({ to: PAYER }))
);
write(
  "payment_underpaid.json",
  await sign("eip155:84532", base({ value: "1" }))
);
write(
  "payment_expired.json",
  await sign("eip155:84532", base({ validBefore: "1000" }))
);
write(
  "payment_bad_signature.json",
  await sign("eip155:84532", base()).then((p) => ({
    ...p,
    payload: { ...p.payload, signature: p.payload.signature.slice(0, -2) + "ff" },
  }))
);

console.log("fixtures written to", out);
