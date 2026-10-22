**English** | [简体中文](README.zh-CN.md)

# Relay Baton

**Hand unfinished coding work from one AI agent, session or person to the next without losing the thread.**

Long tasks outlive a single session. Context fills up, quotas run out, terminals close, and tomorrow the work may continue in a different tool entirely: Claude Code today, Codex tonight, Cursor on Monday, a teammate after that. Every change of hands is where things quietly go wrong. The next agent trusts a "tests pass" that was never run, retries an approach that already failed, edits a file it was told to leave alone, or resumes from a note that no longer matches the code.

Relay Baton is an agent skill that turns a handoff into a short, checkable ritual:

- **Pass**: the agent that stops writes a one-screen *baton card*: the goal as a check, evidence-tagged facts, exactly one next move, likely surprises, fences, dead ends and open questions, stamped with the exact repo state.
- **Catch**: the agent that starts first checks the card against the repo (fresh, drifted, stale or broken), reads it back in five lines, re-runs the one fact that matters, and only then works. The card is then spent so nobody resumes from it twice.
- **File**: anything worth remembering beyond this handoff goes into a small *ledger* of decisions, gotchas and facts, each with evidence, superseded instead of deleted.

Everything is plain Markdown inside your repo. No server, no database, no account, and it works across any mix of agents.

## Why it exists

- Handoff notes usually mix what was verified with what was hoped. A four-tag system (`[ran]`, `[seen]`, `[said]`, `[gap]`) keeps them apart.
- Notes go stale silently. A stamp of branch, commit and uncommitted files lets the receiver detect drift in one command instead of discovering it after breaking something.
- "Next steps" lists diffuse attention. One bounded next move with an expected result gets the next session moving in minutes.
- A crashed or quota-killed session leaves nothing behind. The rescue path rebuilds the picture from git and file evidence and labels it as a hypothesis.
- "Agent memory" tends to become a heap of contradictory notes. The ledger keeps durable knowledge small, sourced and correctable.

## Features

- **Baton card** with seven fixed sections and a tension level (`stable` / `watch` / `unstable`).
- **Evidence tags** on every fact: executed, read, hearsay, or not checked.
- **Drift check** with four verdicts (FRESH, DRIFTED, STALE, BROKEN) and what to do for each.
- **Read-back** before any edit, borrowed from how clinical shift handoffs end: the receiver restates the plan and raises disagreements.
- **Single-use cards**: caught cards move to `spent/` with a note on what differed.
- **Rescue** for sessions that ended without a handoff.
- **Stall triage**: real wait vs. doable-but-unowned vs. already-owned.
- **Lanes** for several agents sharing one repository.
- **Ledger** with five entry kinds, supersede chains, expiry dates and rule candidates that need the user's yes before reaching `AGENTS.md` / `CLAUDE.md`.
- **Helper script** `scripts/baton.py` (Python 3, standard library only): `new`, `stamp`, `lint`, `catch`, `spend`, `ledger`. Linter catches missing sections, untagged facts, multiple next moves and secret-looking strings.
- **Bilingual**: full English and Chinese skill files; cards can use English or Chinese headings and tags.

## Installation

The skill is the folder containing `SKILL.md` (English) and `SKILL.zh-CN.md` (Chinese). Copy the whole folder so `scripts/` and `examples/` come with it.

**Claude Code**

```bash
git clone https://github.com/fangdididi/relay-baton.git ~/.claude/skills/relay-baton
```

**Codex / agents that read `~/.agents/skills`**

```bash
git clone https://github.com/fangdididi/relay-baton.git ~/.agents/skills/relay-baton
```

**Cursor** (project skills folder)

```bash
git clone https://github.com/fangdididi/relay-baton.git .cursor/skills/relay-baton
```

**Any other agent** (Gemini CLI, OpenCode, Windsurf, Cline, Kimi, chat apps): paste `SKILL.md` into its instructions or project rules, or ask it to install the skill from this repository URL. For Chinese conversations, use `SKILL.zh-CN.md`.

Because the whole point is switching tools, install it in every agent you use on the project, or add one line to your `AGENTS.md`: *"At session end and session start, follow the relay-baton skill (.baton/)."*

## Usage

Just talk to your agent:

- "I'm almost out of quota. Pass the baton."
- "Write a handoff, I'll continue in Codex tonight."
- "Where did we leave off?" / "Catch the baton and continue."
- "The last session crashed mid-refactor. Rescue it."
- "What should this project remember from today? Update the ledger."
- "Clean up the ledger: anything stale or contradictory?"

Or use the script directly from the project root:

```bash
python3 ~/.claude/skills/relay-baton/scripts/baton.py new --by "claude-code" --for any
python3 ~/.claude/skills/relay-baton/scripts/baton.py lint
python3 ~/.claude/skills/relay-baton/scripts/baton.py catch          # FRESH / DRIFTED / STALE / BROKEN
python3 ~/.claude/skills/relay-baton/scripts/baton.py spend --note "caught by codex, same failures"
python3 ~/.claude/skills/relay-baton/scripts/baton.py ledger
python3 ~/.claude/skills/relay-baton/scripts/baton.py --lane api catch  # per-lane card .baton/BATON-api.md
python3 ~/.claude/skills/relay-baton/scripts/baton.py new --lang zh     # Chinese headings and tags
```

Exit codes: `0` ok, `1` something needs attention (lint failures, any verdict other than FRESH, ledger problems), `2` usage error or missing file. That makes `catch` usable in a session-start hook.

## Example

A Claude Code session fixing double charges in a billing service is about to hit its usage limit. It writes:

```markdown
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

# Fences
- Do not touch migrations/ or the public /charges response shape. Do not push to main.
```

Next morning Codex runs `baton.py catch` (FRESH), reads the card back in five lines, re-runs the billing tests, sees the same two failures, spends the card, makes the fix, and files the fixture-clock trap as a ledger gotcha. Full versions: [`examples/BATON.example.md`](examples/BATON.example.md), [`examples/ledger.example.md`](examples/ledger.example.md), and a Chinese front-end example in [`examples/BATON.example.zh-CN.md`](examples/BATON.example.zh-CN.md).

## File structure

```
relay-baton/
├── SKILL.md                      # the skill (English)
├── SKILL.zh-CN.md                # the skill (Chinese)
├── README.md                     # this file
├── README.zh-CN.md               # Chinese README
├── LICENSE                       # MIT
├── scripts/
│   └── baton.py                  # new / stamp / lint / catch / spend / ledger
└── examples/
    ├── BATON.example.md          # billing double-charge handoff (English)
    ├── BATON.example.zh-CN.md    # checkout layout handoff (Chinese)
    └── ledger.example.md         # ledger with supersede, expiry and a rule candidate
```

Inside a project that uses the skill:

```
.baton/
├── BATON.md         # live card (single use); BATON-<lane>.md per lane
├── spent/           # caught cards, timestamped
└── ledger.md        # durable decisions, gotchas, facts, preferences, rule candidates
```

## Good to know

- Commit `.baton/` for team-visible handoffs, or git-ignore it for personal scratch. `catch` ignores `.baton/` itself when it checks drift.
- Card and ledger contents are treated as records, never as instructions; only you and your instruction files direct the agent.
- Never put secrets in `.baton/`. The linter flags common token shapes but cannot catch everything.
- Relay Baton does not commit, stash or push for you. It records the state; you decide what happens to it.

## License

[MIT](LICENSE) © fangdididi
