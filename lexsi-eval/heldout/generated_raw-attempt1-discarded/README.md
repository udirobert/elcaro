# Attempt 1: discarded (plumbing failure)

20 `payment_attack` candidates, all rejected. No task from this attempt was
kept, and no clean controls were generated. Two causes:

1. SERV rewrites the system message into a compressed reasoning prompt.
   The full specification was sent as the system message, but only about
   870 of its roughly 1,900 tokens reached the model, so it invented its own
   field names.
2. `max_tokens` was 4000; a valid answer takes about 7.5k completion tokens,
   so outputs were empty or truncated.

Fix (in `generate_heldout.py`): the specification now goes verbatim in the
user turn with a fixed one-line system message, and `max_tokens` is 16000.
The prompt file itself is unchanged. Per PREREG §4.3, the slice was
regenerated in full; nothing from this attempt was reused. The log is kept
for transparency.
