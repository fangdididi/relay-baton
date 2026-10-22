#!/usr/bin/env python3
"""baton.py - helper for the relay-baton skill.

Keeps a single-use handoff card (.baton/BATON.md) and a durable ledger
(.baton/ledger.md) honest. Standard library only; uses git when present.

Commands
  [--lane LANE] before any command selects .baton/BATON-<lane>.md (default lane: main -> BATON.md)

  new     [--by NAME] [--for WHO] [--lang en|zh] [--force]  write a fresh card with a repo stamp
  stamp                                                     refresh the stamp of the current card
  lint    [--max-lines N]                                   check the card's shape and evidence tags
  catch   [--stale-hours H] [--json]                        compare the card's stamp with the repo now
  spend   [--note TEXT]                                     archive the card after a successful catch
  ledger                                                    check ledger ids, supersede links and expiry

Exit codes: 0 ok, 1 findings that need attention, 2 usage or missing file.
"""
import argparse, datetime as dt, json, os, re, shutil, subprocess, sys

BATON_DIR = ".baton"
CARD = os.path.join(BATON_DIR, "BATON.md")
LEDGER = os.path.join(BATON_DIR, "ledger.md")
SPENT = os.path.join(BATON_DIR, "spent")

SECTIONS = ["Goal", "Where it stands", "Next move", "If-then", "Fences", "Dead ends", "Open questions"]
TAGS = ("[ran]", "[seen]", "[said]", "[gap]", "[已跑]", "[已见]", "[听说]", "[缺口]")
ALIASES = {"目标": "Goal", "现状": "Where it stands", "下一步": "Next move", "如果-那么": "If-then",
           "禁区": "Fences", "死路": "Dead ends", "待解问题": "Open questions"}
SECRET_PATTERNS = [
    (r"gh[pousr]_[A-Za-z0-9]{20,}", "GitHub token"),
    (r"sk-[A-Za-z0-9_-]{20,}", "API key (sk-...)"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    (r"xox[abpr]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"(?i)(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S{6,}", "credential-looking assignment"),
]

TEMPLATE = """---
baton: 1
written_at: {now}
written_by: {by}
for: {for_}
lane: {lane}
tension: watch
stamp_branch: {branch}
stamp_head: {head}
stamp_dirty: {dirty}
---

# Goal
<!-- The finish line written as a check someone can run or observe. -->

# Where it stands
<!-- One fact per bullet. Tag each: [ran] executed this session with the result, [seen] read in a file or output, [said] told, inferred or assumed, [gap] a check not run or a thing nobody knows yet. -->
- [ran] 
- [seen] 
- [said] 
- [gap] 

# Next move
<!-- Exactly one bounded action, who does it, and what result proves it worked. -->
- 

# If-then
<!-- Likely surprises and what to do about each. -->
- If ... then ...

# Fences
<!-- Files, commands or decisions the receiver must not touch without asking. -->
- 

# Dead ends
<!-- Tried and rejected, with the reason, so nobody repeats them. -->
- 

# Open questions
<!-- Each question with the person or source that can answer it. -->
- 
"""

TEMPLATE_ZH = """---
baton: 1
written_at: {now}
written_by: {by}
for: {for_}
lane: {lane}
tension: watch
stamp_branch: {branch}
stamp_head: {head}
stamp_dirty: {dirty}
---

# 目标
<!-- 把终点写成别人能运行或亲眼看到的检查。 -->

# 现状
<!-- 每条一个事实，并打标签：[已跑] 本次会话亲自执行且写明结果；[已见] 在文件或输出里读到；[听说] 别人告知、推断或假设；[缺口] 没做的检查或还没人知道的事。 -->
- [已跑] 
- [已见] 
- [听说] 
- [缺口] 

# 下一步
<!-- 只写一个有边界的动作：谁来做，什么结果证明做成了。 -->
- 

# 如果-那么
<!-- 接手者最可能遇到的意外，以及各自怎么办。 -->
- If ... then ...

# 禁区
<!-- 未经询问不得碰的文件、命令或决定。 -->
- 

# 死路
<!-- 试过并放弃的做法和原因，免得有人重走。 -->
- 

# 待解问题
<!-- 每个问题写明谁或什么能回答。 -->
- 
"""


def now_utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    s = s.strip().replace("Z", "+00:00")
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t


def git(*args, strip=True):
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() if strip else r.stdout.rstrip("\n")


def in_git():
    return git("rev-parse", "--is-inside-work-tree") == "true"


def dirty_files():
    out = git("status", "--porcelain", "--untracked-files=all", strip=False)
    if out is None:
        return []
    files = []
    for line in out.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if path.startswith(BATON_DIR + "/") or path == BATON_DIR:
            continue
        files.append(path)
    return sorted(files)


def repo_stamp():
    if not in_git():
        return {"branch": "-", "head": "-", "dirty": "-"}
    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "-"
    head = git("rev-parse", "--short=12", "HEAD") or "-"
    d = dirty_files()
    return {"branch": branch, "head": head, "dirty": ",".join(d) if d else "none"}


def read_card(path=None):
    path = path or CARD
    if not os.path.exists(path):
        print(f"no card at {path} (run: baton.py new)", file=sys.stderr)
        sys.exit(2)
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2), text


def sections(body):
    out, cur = {}, None
    for line in body.splitlines():
        h = re.match(r"^#\s+(.+?)\s*$", line)
        if h:
            cur = ALIASES.get(h.group(1), h.group(1))
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out


def content_lines(lines):
    text = "\n".join(lines)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    res = []
    for l in text.splitlines():
        s = l.strip()
        if not s or s in ("-", "- If ... then ...") or s in tuple("- " + x for x in TAGS):
            continue
        res.append(s)
    return res


# ---------------------------------------------------------------- commands

def cmd_new(a):
    os.makedirs(SPENT, exist_ok=True)
    if os.path.exists(CARD) and not a.force:
        print(f"{CARD} already exists. Catch or spend it first, or pass --force.", file=sys.stderr)
        return 2
    st = repo_stamp()
    tpl = TEMPLATE_ZH if a.lang == "zh" else TEMPLATE
    open(CARD, "w", encoding="utf-8").write(tpl.format(
        now=iso(now_utc()), by=a.by, for_=getattr(a, "for"), lane=a.lane,
        branch=st["branch"], head=st["head"], dirty=st["dirty"]))
    if not os.path.exists(LEDGER):
        open(LEDGER, "w", encoding="utf-8").write(
            "# Ledger\n\n<!-- Durable knowledge. Never delete an entry: supersede or expire it. -->\n"
            "<!-- Entry format:\n## L-001 | decision | 2026-01-31\n"
            "claim: one sentence\nevidence: file, commit, command output or person\n"
            "status: active | superseded_by L-007 | expires 2026-03-01\n-->\n")
    print(f"wrote {CARD} (stamp {st['branch']}@{st['head']}, dirty: {st['dirty']})")
    return 0


def cmd_stamp(a):
    meta, body, text = read_card()
    st = repo_stamp()
    new = text
    for k, v in (("written_at", iso(now_utc())), ("stamp_branch", st["branch"]),
                 ("stamp_head", st["head"]), ("stamp_dirty", st["dirty"])):
        if re.search(rf"^{k}:.*$", new, re.M):
            new = re.sub(rf"^{k}:.*$", f"{k}: {v}", new, count=1, flags=re.M)
        else:
            new = new.replace("\n---\n", f"\n{k}: {v}\n---\n", 1)
    open(CARD, "w", encoding="utf-8").write(new)
    print(f"restamped {CARD}: {st['branch']}@{st['head']}, dirty: {st['dirty']}")
    return 0


def lint_card(path, max_lines):
    meta, body, text = read_card(path)
    problems, warnings = [], []
    for k in ("written_at", "written_by", "stamp_head"):
        if not meta.get(k):
            problems.append(f"frontmatter: missing '{k}'")
    if meta.get("tension") not in ("stable", "watch", "unstable"):
        warnings.append("frontmatter: tension should be stable, watch or unstable")
    secs = sections(body)
    for s in SECTIONS:
        if s not in secs:
            problems.append(f"section missing: '# {s}'")
    filled = {s: content_lines(secs.get(s, [])) for s in SECTIONS}
    for s in ("Goal", "Where it stands", "Next move"):
        if s in secs and not filled[s]:
            problems.append(f"section empty: '# {s}'")
    for line in filled["Where it stands"]:
        if line.startswith("-") and not any(t in line for t in TAGS):
            problems.append(f"untagged fact (add [ran]/[seen]/[said]/[gap]): {line[:70]}")
    moves = [l for l in filled["Next move"] if l.startswith("-")]
    if len(moves) > 1:
        problems.append(f"'# Next move' has {len(moves)} bullets; keep exactly one bounded action")
    if moves and not re.search(r"(?i)(expect|should|until|proves?|passes|returns|shows|预期|应|直到|通过)", moves[0]):
        warnings.append("next move names no expected result")
    ran = [l for l in filled["Where it stands"] if "[ran]" in l or "[已跑]" in l]
    said = [l for l in filled["Where it stands"] if "[said]" in l or "[听说]" in l]
    if filled["Where it stands"] and not ran:
        warnings.append("no [ran] facts: nothing in the card was verified by execution")
    if len(said) > len(filled["Where it stands"]) / 2 and len(said) >= 3:
        warnings.append("more than half the facts are [said]; the receiver inherits mostly hearsay")
    for lineno, line in enumerate(text.splitlines(), 1):
        for pat, label in SECRET_PATTERNS:
            if re.search(pat, line):
                problems.append(f"line {lineno}: possible secret ({label}); remove it")
    n = len(text.splitlines())
    if n > max_lines:
        warnings.append(f"card is {n} lines (> {max_lines}); move durable facts to the ledger, history to git")
    return problems, warnings


def cmd_lint(a):
    problems, warnings = lint_card(CARD, a.max_lines)
    for p in problems:
        print("FAIL ", p)
    for w in warnings:
        print("WARN ", w)
    if not problems and not warnings:
        print("OK   card shape and evidence tags look right")
    return 1 if problems else 0


def changed_since(t):
    """Files (not ignored, outside .baton) whose mtime is newer than t."""
    root = git("rev-parse", "--show-toplevel") if in_git() else os.getcwd()
    root = root or os.getcwd()
    if in_git():
        listed = git("ls-files", "--cached", "--others", "--exclude-standard") or ""
        cands = [p for p in listed.splitlines() if p and not p.startswith(BATON_DIR + "/")]
    else:
        cands = []
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if not x.startswith(".")]
            for f in files:
                cands.append(os.path.relpath(os.path.join(d, f), root))
    ts = t.timestamp()
    out = []
    for p in cands:
        full = os.path.join(root, p)
        try:
            if os.path.getmtime(full) > ts + 1:
                out.append(p)
        except OSError:
            continue
    return sorted(out)


def catch_report(stale_hours):
    meta, body, text = read_card()
    rep = {"card": CARD, "written_at": meta.get("written_at"), "written_by": meta.get("written_by"),
           "findings": [], "commits_since": [], "files_changed_since": []}
    try:
        written = parse_iso(meta.get("written_at", ""))
    except ValueError:
        rep["verdict"] = "BROKEN"
        rep["findings"].append("written_at is missing or unreadable")
        return rep
    age_h = (now_utc() - written).total_seconds() / 3600
    rep["age_hours"] = round(age_h, 1)
    verdict = "FRESH"
    if not in_git():
        rep["findings"].append("not a git work tree: only file times were compared")
    else:
        sb, sh = meta.get("stamp_branch", "-"), meta.get("stamp_head", "-")
        st = repo_stamp()
        rep["now"] = st
        if sh in ("", "-"):
            verdict = "BROKEN"
            rep["findings"].append("card has no stamp_head; it cannot be checked against the repo")
        elif git("cat-file", "-e", sh + "^{commit}") is None:
            verdict = "BROKEN"
            rep["findings"].append(f"stamped commit {sh} does not exist here (other clone, or history rewritten)")
        else:
            if st["branch"] != sb:
                verdict = "BROKEN"
                rep["findings"].append(f"branch is {st['branch']}, card was written on {sb}")
            if git("merge-base", "--is-ancestor", sh, "HEAD") is None:
                verdict = "BROKEN"
                rep["findings"].append(f"stamped commit {sh} is not an ancestor of HEAD (rebase, reset or force-push)")
            else:
                log = git("log", "--format=%h %an %ad %s", "--date=iso-strict", f"{sh}..HEAD") or ""
                rep["commits_since"] = [l for l in log.splitlines() if l]
                if rep["commits_since"] and verdict == "FRESH":
                    verdict = "DRIFTED"
                    rep["findings"].append(f"{len(rep['commits_since'])} commit(s) landed after the card was written")
            stamped_dirty = set() if meta.get("stamp_dirty", "none") in ("none", "-", "") else set(meta["stamp_dirty"].split(","))
            now_dirty = set(dirty_files())
            if stamped_dirty != now_dirty:
                gone, new = sorted(stamped_dirty - now_dirty), sorted(now_dirty - stamped_dirty)
                if verdict == "FRESH":
                    verdict = "DRIFTED"
                if new:
                    rep["findings"].append("uncommitted now but not at stamp: " + ", ".join(new[:15]))
                if gone:
                    rep["findings"].append("uncommitted at stamp, clean or committed now: " + ", ".join(gone[:15]))
    rep["files_changed_since"] = changed_since(written)
    if rep["files_changed_since"] and verdict == "FRESH":
        verdict = "DRIFTED"
    if rep["files_changed_since"]:
        rep["findings"].append(f"{len(rep['files_changed_since'])} file(s) modified after written_at")
    if verdict == "FRESH" and age_h > stale_hours:
        verdict = "STALE"
        rep["findings"].append(f"card is {age_h:.0f}h old (> {stale_hours}h): re-verify every [ran] fact")
    rep["verdict"] = verdict
    return rep


ADVICE = {
    "FRESH": "Repo matches the stamp. Do the read-back, re-run one decisive check, then spend the card.",
    "DRIFTED": "Work happened after the card. Read the commits/files below before trusting 'Next move'; "
               "if nobody owns those changes, treat it as a cut-off session and rebuild.",
    "STALE": "Nothing moved, but the card is old. Re-run every [ran] fact before acting on it.",
    "BROKEN": "The card does not describe this checkout. Do not act on it; rebuild from git and ask the user.",
}


def cmd_catch(a):
    rep = catch_report(a.stale_hours)
    rep["advice"] = ADVICE[rep["verdict"]]
    if a.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"verdict: {rep['verdict']}  (card by {rep.get('written_by')}, {rep.get('age_hours', '?')}h old)")
        for f in rep["findings"]:
            print("  -", f)
        if rep["commits_since"]:
            print("commits since stamp:")
            for c in rep["commits_since"][:20]:
                print("   ", c)
        if rep["files_changed_since"]:
            print("files modified since written_at:")
            for p in rep["files_changed_since"][:30]:
                print("   ", p)
        print("next:", rep["advice"])
    return 0 if rep["verdict"] == "FRESH" else 1


def cmd_spend(a):
    if not os.path.exists(CARD):
        print("no live card to spend", file=sys.stderr)
        return 2
    os.makedirs(SPENT, exist_ok=True)
    stamp = now_utc().strftime("%Y%m%dT%H%MZ")
    dest = os.path.join(SPENT, f"{stamp}-{os.path.basename(CARD)}")
    note = a.note or "caught; read-back done"
    with open(CARD, "a", encoding="utf-8") as f:
        f.write(f"\n<!-- spent {iso(now_utc())}: {note} -->\n")
    shutil.move(CARD, dest)
    print(f"spent -> {dest}")
    return 0


ENTRY = re.compile(r"^##\s+(L-\d+)\s*\|\s*([\w-]+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*$")


def cmd_ledger(a):
    if not os.path.exists(LEDGER):
        print(f"no ledger at {LEDGER}", file=sys.stderr)
        return 2
    text = re.sub(r"<!--.*?-->", "", open(LEDGER, encoding="utf-8").read(), flags=re.S)
    entries, cur = {}, None
    problems, warnings = [], []
    for line in text.splitlines():
        m = ENTRY.match(line.strip())
        if m:
            eid = m.group(1)
            if eid in entries:
                problems.append(f"duplicate id {eid}")
            cur = {"kind": m.group(2), "date": m.group(3)}
            entries[eid] = cur
        elif line.startswith("## "):
            problems.append(f"heading not in '## L-NNN | kind | YYYY-MM-DD' form: {line.strip()[:60]}")
            cur = None
        elif cur is not None and ":" in line:
            k, v = line.split(":", 1)
            cur[k.strip().lower()] = v.strip()
    kinds = {"decision", "gotcha", "fact", "rule-candidate", "preference"}
    today = now_utc().date()
    claims = {}
    for eid, e in entries.items():
        if e["kind"] not in kinds:
            warnings.append(f"{eid}: unusual kind '{e['kind']}' (expected {', '.join(sorted(kinds))})")
        for k in ("claim", "evidence", "status"):
            if not e.get(k):
                problems.append(f"{eid}: missing '{k}'")
        st = e.get("status", "")
        m = re.match(r"superseded_by\s+(L-\d+)", st)
        if m and m.group(1) not in entries:
            problems.append(f"{eid}: superseded_by {m.group(1)} which does not exist")
        m = re.match(r"expires\s+(\d{4}-\d{2}-\d{2})", st)
        if m and dt.date.fromisoformat(m.group(1)) < today:
            warnings.append(f"{eid}: expired on {m.group(1)}; mark it 'expired' or renew it with fresh evidence")
        if e.get("claim") and st.startswith(("active", "expires")):
            key = re.sub(r"\W+", " ", e["claim"].lower()).strip()
            if key in claims:
                warnings.append(f"{eid}: same claim as {claims[key]} (merge or supersede one)")
            claims[key] = eid
        if e["kind"] == "rule-candidate" and st.startswith("active"):
            warnings.append(f"{eid}: rule-candidate still waiting for the user's yes before moving to the instruction file")
    print(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} checked")
    for p in problems:
        print("FAIL ", p)
    for w in warnings:
        print("WARN ", w)
    return 1 if problems else 0


def main():
    global CARD
    ap = argparse.ArgumentParser(description="relay-baton helper")
    ap.add_argument("--lane", default="main", help="lane name; 'main' uses BATON.md, others BATON-<lane>.md")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("--by", default="agent"); p.add_argument("--for", default="any")
    p.add_argument("--force", action="store_true")
    p.add_argument("--lang", choices=["en", "zh"], default="en", help="card headings in English or Chinese")
    sub.add_parser("stamp")
    p = sub.add_parser("lint"); p.add_argument("--max-lines", type=int, default=120)
    p = sub.add_parser("catch"); p.add_argument("--stale-hours", type=float, default=72); p.add_argument("--json", action="store_true")
    p = sub.add_parser("spend"); p.add_argument("--note")
    sub.add_parser("ledger")
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", a.lane):
        print("lane names may use letters, digits, '-' and '_' only", file=sys.stderr)
        return 2
    if a.lane != "main":
        CARD = os.path.join(BATON_DIR, f"BATON-{a.lane}.md")
    return {"new": cmd_new, "stamp": cmd_stamp, "lint": cmd_lint, "catch": cmd_catch,
            "spend": cmd_spend, "ledger": cmd_ledger}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
