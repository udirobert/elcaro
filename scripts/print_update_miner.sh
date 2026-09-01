#!/usr/bin/env bash
# Print the updateMiner() command for the current miner/telegraph.yaml.
#
# Deploy the YAML to https://api.elcaro.trustfall.xyz/telegraph.yaml FIRST,
# then run this and send the tx from the registering wallet. Hashing a local
# file that differs in line endings from what the node fetches will reject.
set -euo pipefail

YAML_URL="${YAML_URL:-https://api.elcaro.trustfall.xyz/telegraph.yaml}"
DIAMOND="${DIAMOND:-0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8}"
REGISTRATION_ID="${REGISTRATION_ID:-406}"
FEE_ADDRESS="${FEE_ADDRESS:-0x1e17B4FB12B29045b29475f74E536Db97Ddc5D40}"
MIN_PRICE="${MIN_PRICE:-10000}"
LOCAL_YAML="$(cd "$(dirname "$0")/.." && pwd)/miner/telegraph.yaml"

echo "local file:  $LOCAL_YAML"
echo "live URL:    $YAML_URL"
echo

LOCAL_HASH="$(shasum -a 256 "$LOCAL_YAML" | awk '{print "0x"$1}')"
LIVE_HASH="$(curl -fsS "$YAML_URL" | shasum -a 256 | awk '{print "0x"$1}')"

echo "local sha256: $LOCAL_HASH"
echo "live  sha256: $LIVE_HASH"
echo

if [ "$LOCAL_HASH" != "$LIVE_HASH" ]; then
  echo "WARNING: live URL does not match the local file."
  echo "Deploy miner/telegraph.yaml, then re-run this script."
  echo "Sending updateMiner against the local hash while the URL still"
  echo "serves the old bytes will reject the miner."
  echo
fi

echo "cast send \"$DIAMOND\" \\"
echo "  \"updateMiner(uint256,string,bytes32,address,uint256,string[])\" \\"
echo "  $REGISTRATION_ID \\"
echo "  \"$YAML_URL\" \\"
echo "  \"$LIVE_HASH\" \\"
echo "  \"$FEE_ADDRESS\" \\"
echo "  $MIN_PRICE \\"
echo "  '[\"CONTENT_MODERATION\",\"TEXT_CLASSIFICATION\"]' \\"
echo "  --rpc-url \"\$RPC\" \\"
echo "  --private-key \"\$MINER_PRIVATE_KEY\""
echo
echo "After the tx confirms, update miner/config.yaml registration_id to the"
echo "new id from the MinerRegistered event (updateMiner issues a new one)."
