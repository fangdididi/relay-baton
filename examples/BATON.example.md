---
baton: 1
written_at: 2026-10-22T03:10:00Z
written_by: claude-code (billing retry session)
for: any
lane: main
tension: watch
stamp_branch: fix/double-charge
stamp_head: 4be21c90a7d3
stamp_dirty: src/billing/retry.py,tests/billing/test_replay.py
---
# Goal
`pytest tests/billing` is green, and replaying one webhook twice produces exactly one charge row.

# Where it stands
- [ran] pytest tests/billing -> 2 failed (test_replay, test_refund), 31 passed
- [seen] src/billing/retry.py:41 calls charge() before the idempotency key is stored
- [seen] test_refund fails on a date assertion, unrelated to retry (fixture clock)
- [said] user says the payments sandbox accepts duplicate keys silently
- [gap] e2e suite not run: needs Docker, not available in this session

# Next move
- Any agent: store the idempotency key before charge() in retry.py; expect test_replay to pass and test_refund to stay failing for its own reason.

# If-then
- If test_replay still fails, check the key format: the sandbox wants <=64 chars.
- If more than these two tests fail, stop: something else changed on the branch.

# Fences
- Do not touch migrations/ or the public /charges response shape.
- Do not push to main; the user reviews this branch.

# Dead ends
- Wrapping charge() in a DB transaction: the provider call is outside the DB, so it does not prevent a second charge.

# Open questions
- Should old duplicate rows be cleaned up? Ask the user (data change).
