# Ledger

<!-- Durable knowledge. Never delete an entry: supersede or expire it. -->

## L-003 | decision | 2026-10-14
claim: Payment retries are keyed by order id plus attempt group, not by request id.
evidence: commit 9c1e0aa; discussion with the user on 2026-10-14
status: superseded_by L-008

## L-005 | preference | 2026-10-17
claim: The user reviews every change to the billing package before merge; agents open a branch, never push to main.
evidence: user instruction, 2026-10-17 session
status: active

## L-006 | fact | 2026-10-18
claim: The payments sandbox accepts a reused idempotency key without an error, so duplicates only show up in our own table.
evidence: sandbox docs page "Testing"; reproduced with scripts/replay_webhook.sh
status: expires 2027-01-31

## L-007 | gotcha | 2026-10-22
claim: Billing fixtures freeze time at UTC midnight, so refund-window tests fail for reasons unrelated to the code under test.
evidence: tests/fixtures/clock.py:12; pytest tests/billing/test_refund.py
status: active

## L-008 | decision | 2026-10-22
claim: The idempotency key is the order id alone and is stored before calling the provider.
evidence: commit 51d7f3b; tests/billing/test_replay.py
status: active

## L-009 | rule-candidate | 2026-10-22
claim: Never call charge() directly; always go through retry(), which stores the key first.
evidence: double-charge incident fixed in 51d7f3b
status: active
