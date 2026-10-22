#!/usr/bin/env python3
"""
wo.py - Work-order dispatcher for the Claude (foreman) + Codex/Claude Code (workers) setup.

Standard library only. Python 3.10+. Works on Windows, macOS and Linux.

Run from anywhere inside the repo:

    python orchestration/scripts/wo.py <command> [args]

Commands
    init                         Create folders and .gitignore entries
    new "Title" [opts]           Create a work order from the template (status: draft)
    board                        Show all work orders grouped by status
    show WO-001                  Print one work order
    set WO-001 key=value ...     Edit front-matter fields (status, assignee, ...)
    dispatch WO-001 [--agent X]  Run one work order now (foreground)
    run-ready [--max N]          Run every 'ready' work order whose dependencies are done, in parallel
    review WO-001 [--agent X]    Cross-review a finished work order with the *other* agent
    rework WO-001 "notes"        Append rework notes and send it back to the queue
    merge WO-001                 Merge the work-order branch into main and clean up
    cleanup WO-001               Remove the worktree (and branch with --delete-branch)
    ledger                       Usage per agent vs. the target split

Add --dry-run to dispatch / run-ready / review to print what would run without running it.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

STATUSES = ["draft", "ready", "in_progress", "review", "rework", "blocked", "done"]
AGENTS = ["codex", "claude"]
_ledger_lock = threading.Lock()
_wo_lock = threading.Lock()
_gpu_lock = threading.Lock()


# --------------------------------------------------------------------------- paths / config

def repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("wo.py: run this inside the game's git repository.")
    return Path(out.stdout.strip())


ROOT = None  # set in main()


def orch() -> Path:
    return ROOT / "orchestration"


def wo_dir() -> Path:
    return orch() / "work-orders"


def runs_dir() -> Path:
    return orch() / "runs"


DEFAULT_CONFIG = {
    "main_branch": "main",
    "worktree_root": "../{repo}-worktrees",
    "target_split": {"codex": 0.65, "claude": 0.35},
    "balance_window_runs": 20,
    "max_parallel": {"codex": 2, "claude": 1},
    "timeout_minutes": 60,
    "rate_limit_cooldown_minutes": 60,
    "test_command": [],
    "agents": {
        "codex": {
            "work": ["codex", "exec", "--sandbox", "workspace-write", "--json",
                     "--output-last-message", "{last_message_file}", "-"],
            "review": ["codex", "exec", "--sandbox", "read-only",
                       "--output-last-message", "{last_message_file}", "-"],
            "output": "codex-jsonl",
            "rate_limit_patterns": ["rate limit", "rate_limit", "usage limit", "429"],
        },
        "claude": {
            "work": ["claude", "-p", "--permission-mode", "acceptEdits",
                     "--allowedTools", "Bash(git *),Bash(godot *),Bash(python *),Bash(py *)",
                     "--output-format", "json"],
            "review": ["claude", "-p", "--permission-mode", "dontAsk",
                       "--allowedTools", "Read,Grep,Glob,Bash(git diff *),Bash(git log *)",
                       "--output-format", "json"],
            "output": "claude-json",
            "rate_limit_patterns": ["rate limit", "rate_limit", "usage limit", "429"],
        },
    },
}


def load_config() -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    path = orch() / "config.json"
    if path.exists():
        user = json.loads(path.read_text(encoding="utf-8"))
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def worktree_root(cfg) -> Path:
    raw = cfg["worktree_root"].replace("{repo}", ROOT.name)
    p = Path(raw)
    return (ROOT / p).resolve() if not p.is_absolute() else p


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def git(*args, cwd=None, check=True) -> subprocess.CompletedProcess:
    res = subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{res.stderr.strip()}")
    return res


# --------------------------------------------------------------------------- work-order files

class WorkOrder:
    """A markdown file with a simple front-matter block (key: value, lists as [a, b])."""

    def __init__(self, path: Path):
        self.path = path
        text = path.read_text(encoding="utf-8")
        m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
        if not m:
            raise ValueError(f"{path.name}: missing front-matter block")
        self.keys: list[str] = []
        self.meta: dict = {}
        for line in m.group(1).splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            self.keys.append(k)
            self.meta[k] = _parse_value(v)
        self.body = m.group(2)

    @property
    def id(self) -> str:
        return str(self.meta.get("id"))

    def get(self, k, default=None):
        v = self.meta.get(k, default)
        return default if v in ("", None) else v

    def set(self, k, v):
        if k not in self.keys:
            self.keys.append(k)
        self.meta[k] = v

    def save(self):
        lines = ["---"] + [f"{k}: {_format_value(self.meta[k])}" for k in self.keys] + ["---"]
        self.path.write_text("\n".join(lines) + "\n" + self.body, encoding="utf-8")

    def append_body(self, text: str):
        if not self.body.endswith("\n"):
            self.body += "\n"
        self.body += text


def _parse_value(v: str):
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    return v.strip("'\"")


def _format_value(v) -> str:
    if isinstance(v, list):
        return "[" + ", ".join(v) + "]"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def all_wos() -> list[WorkOrder]:
    out = []
    for p in sorted(wo_dir().glob("WO-*.md")):
        try:
            out.append(WorkOrder(p))
        except ValueError as e:
            print(f"warning: {e}", file=sys.stderr)
    return out


def find_wo(wo_id: str) -> WorkOrder:
    wo_id = wo_id.upper()
    if re.fullmatch(r"\d+", wo_id):
        wo_id = f"WO-{int(wo_id):03d}"
    for wo in all_wos():
        if wo.id.upper() == wo_id:
            return wo
    sys.exit(f"wo.py: no work order {wo_id}")


def update_wo(wo_id: str, fn):
    """Re-read, modify and save a work order under a lock (safe with parallel runs)."""
    with _wo_lock:
        wo = find_wo(wo_id)
        fn(wo)
        wo.save()
        return wo


# --------------------------------------------------------------------------- ledger / routing

def ledger_path() -> Path:
    return runs_dir() / "ledger.jsonl"


def read_ledger() -> list[dict]:
    p = ledger_path()
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def write_ledger(row: dict):
    with _ledger_lock:
        runs_dir().mkdir(parents=True, exist_ok=True)
        with ledger_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")


def in_cooldown(agent: str, cfg) -> bool:
    cutoff = time.time() - cfg["rate_limit_cooldown_minutes"] * 60
    return any(r.get("agent") == agent and r.get("rate_limited") and r.get("ts", 0) >= cutoff
               for r in read_ledger())


def usage_share(cfg) -> dict:
    rows = [r for r in read_ledger() if r.get("kind") == "work"][-cfg["balance_window_runs"]:]
    minutes = {a: 0.0 for a in AGENTS}
    for r in rows:
        if r.get("agent") in minutes:
            minutes[r["agent"]] += r.get("minutes", 0)
    total = sum(minutes.values())
    return {a: (minutes[a] / total if total else 0.0) for a in AGENTS}


def choose_agent(wo: WorkOrder, cfg, override: str | None = None) -> tuple[str | None, str]:
    """Return (agent, reason). Agent is None if nobody can take it right now."""
    if override:
        return override, "forced with --agent"
    want = str(wo.get("assignee", "either")).lower()
    fallback = wo.get("fallback", True)
    available = [a for a in AGENTS if not in_cooldown(a, cfg)]
    if want in AGENTS:
        if want in available:
            return want, "assigned"
        other = [a for a in available if a != want]
        if fallback and other:
            return other[0], f"{want} is rate-limited; fallback allowed"
        return None, f"{want} is rate-limited and fallback is off"
    if not available:
        return None, "both agents are rate-limited"
    share = usage_share(cfg)
    target = cfg["target_split"]
    best = max(available, key=lambda a: target.get(a, 0) - share.get(a, 0))
    return best, f"balancing (recent share {share[best]:.0%} vs target {target.get(best, 0):.0%})"


# --------------------------------------------------------------------------- running agents

def render(cmd: list[str], **kw) -> list[str]:
    out = [c.format(**kw) if "{" in c else c for c in cmd]
    exe = shutil.which(out[0])
    if exe:
        out[0] = exe  # resolves .cmd/.exe shims on Windows
    return out


def build_prompt(template_name: str, wo: WorkOrder, branch: str, extra: str = "") -> str:
    tpl = (orch() / "templates" / template_name).read_text(encoding="utf-8")
    return (tpl.replace("{wo_id}", wo.id)
               .replace("{wo_title}", str(wo.get("title", "")))
               .replace("{branch}", branch)
               .replace("{main_branch}", load_config()["main_branch"])
               .replace("{wo_body}", wo.body.strip())
               .replace("{extra}", extra.strip()))


def parse_usage(kind: str, stdout: str, last_msg_file: Path) -> dict:
    info: dict = {}
    if kind == "claude-json":
        try:
            data = json.loads(stdout.strip().splitlines()[-1])
            info["result"] = data.get("result", "")
            info["cost_usd"] = data.get("total_cost_usd")
            u = data.get("usage") or {}
            info["input_tokens"] = u.get("input_tokens")
            info["output_tokens"] = u.get("output_tokens")
            info["is_error"] = data.get("is_error", False)
            last_msg_file.write_text(info["result"] or "", encoding="utf-8")
        except (json.JSONDecodeError, IndexError):
            last_msg_file.write_text(stdout, encoding="utf-8")
    elif kind == "codex-jsonl":
        # Best effort: Codex prints one JSON event per line; keep the last usage-looking numbers seen.
        for line in stdout.splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            for k in ("input_tokens", "output_tokens"):
                v = _find_key(ev, k)
                if isinstance(v, int):
                    info[k] = v
    return info


def _find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def ensure_worktree(wo: WorkOrder, cfg) -> tuple[Path, str]:
    branch = wo.get("branch") or f"wo/{wo.id}"
    path = worktree_root(cfg) / wo.id
    if path.exists():
        return path, branch
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = git("rev-parse", "--verify", "--quiet", branch, check=False).returncode == 0
    if exists:
        git("worktree", "add", str(path), branch)
    else:
        git("worktree", "add", "-b", branch, str(path), cfg["main_branch"])
    return path, branch


def run_tests(cfg, cwd: Path) -> str:
    cmd = cfg.get("test_command") or []
    if not cmd:
        return "not configured"
    try:
        res = subprocess.run(render(cmd), cwd=cwd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=900)
        (cwd / ".wo-test-output.txt").write_text(res.stdout + res.stderr, encoding="utf-8")
        return "PASS" if res.returncode == 0 else "FAIL"
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"ERROR ({e.__class__.__name__})"


def dispatch(wo_id: str, agent_override=None, dry_run=False, reason_override=None) -> dict:
    cfg = load_config()
    wo = find_wo(wo_id)
    deps = [d for d in wo.get("depends_on", []) or []]
    not_done = [d for d in deps if find_wo(d).get("status") != "done"]
    if not_done:
        return {"wo": wo.id, "skipped": f"waiting on {', '.join(not_done)}"}

    agent, reason = choose_agent(wo, cfg, agent_override)
    if reason_override:
        reason = reason_override
    if agent is None:
        return {"wo": wo.id, "skipped": reason}

    rework = wo.get("status") == "rework"
    extra = ""
    if rework:
        notes = wo.body.split("## Rework notes", 1)
        extra = "REWORK REQUESTED. Address these notes from the foreman:\n" + (notes[1] if len(notes) > 1 else "")

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = runs_dir() / wo.id / f"{stamp}-{agent}"
    last_msg = run_dir / "last_message.md"
    acfg = cfg["agents"][agent]
    branch_preview = wo.get("branch") or f"wo/{wo.id}"
    cmd = render(acfg["work"], last_message_file=str(last_msg))

    if dry_run:
        return {"wo": wo.id, "agent": agent, "reason": reason, "branch": branch_preview,
                "worktree": str(worktree_root(cfg) / wo.id), "cmd": cmd}

    path, branch = ensure_worktree(wo, cfg)
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt("worker-prompt.md", wo, branch, extra)
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")

    def mark_start(w):
        w.set("status", "in_progress")
        w.set("branch", branch)
        w.set("last_agent", agent)
    update_wo(wo.id, mark_start)

    gpu = bool(wo.get("gpu", False))
    if gpu:
        _gpu_lock.acquire()
    t0 = time.time()
    try:
        res = subprocess.run(cmd, cwd=path, input=prompt, capture_output=True, text=True,
                             encoding="utf-8", errors="replace",
                             timeout=cfg["timeout_minutes"] * 60)
        code, stdout, stderr = res.returncode, res.stdout, res.stderr
    except subprocess.TimeoutExpired as e:
        code, stdout, stderr = -1, (e.stdout or "") if isinstance(e.stdout, str) else "", "TIMEOUT"
    except OSError as e:
        code, stdout, stderr = -2, "", f"could not start agent: {e}"
    finally:
        if gpu:
            _gpu_lock.release()
    minutes = round((time.time() - t0) / 60, 2)
    (run_dir / "stdout.log").write_text(stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(stderr, encoding="utf-8")
    usage = parse_usage(acfg.get("output", ""), stdout, last_msg)

    haystack = (stdout[-4000:] + stderr[-4000:]).lower()
    rate_limited = code != 0 and any(p in haystack for p in acfg.get("rate_limit_patterns", []))

    # Never lose work: commit anything the agent left uncommitted.
    dirty = git("status", "--porcelain", cwd=path).stdout.strip()
    if dirty:
        first = ""
        if last_msg.exists():
            first = next((l.strip("#*- ").strip() for l in last_msg.read_text(encoding="utf-8").splitlines()
                          if l.strip()), "")
        msg = f"{wo.id}: {first[:68]}" if first else f"{wo.id}: work by {agent}"
        git("add", "-A", cwd=path)
        git("commit", "-m", msg, "-m", f"Committed by wo.py after the {agent} run.", cwd=path, check=False)
    ahead = git("rev-list", "--count", f"{cfg['main_branch']}..{branch}", cwd=path).stdout.strip()

    tests = run_tests(cfg, path) if code == 0 else "skipped"
    if rate_limited:
        new_status = "ready" if not rework else "rework"
    elif code == 0:
        new_status = "review"
    else:
        new_status = "blocked"

    summary = {"wo": wo.id, "agent": agent, "reason": reason, "exit": code, "minutes": minutes,
               "commits_ahead": int(ahead or 0), "tests": tests, "rate_limited": rate_limited,
               "status": new_status, "run_dir": str(run_dir.relative_to(ROOT)), **{
                   k: v for k, v in usage.items() if k != "result"}}
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_ledger({"ts": time.time(), "kind": "work", **summary})

    note = (f"- {now()} {agent}: exit {code}, {minutes} min, {summary['commits_ahead']} commit(s), "
            f"tests {tests} -> {new_status}" + (" (rate-limited)" if rate_limited else "") + "\n")

    def mark_end(w):
        w.set("status", new_status)
        if "## Run log" not in w.body:
            w.append_body("\n## Run log\n")
        w.append_body(note)
    update_wo(wo.id, mark_end)
    return summary


def run_ready(max_total=None, dry_run=False, only_agent=None) -> list[dict]:
    cfg = load_config()
    wos = [w for w in all_wos() if w.get("status") in ("ready", "rework")]
    if max_total:
        wos = wos[:max_total]
    if not wos:
        print("Nothing is ready.")
        return []
    sems = {a: threading.Semaphore(cfg["max_parallel"].get(a, 1)) for a in AGENTS}

    # Assign agents up front so "either" work orders are spread across agents in this batch,
    # using a rough minutes-per-size estimate on top of the recent ledger share.
    est = {"S": 10, "M": 25, "L": 60}
    recent = [r for r in read_ledger() if r.get("kind") == "work"][-cfg["balance_window_runs"]:]
    tally = {a: sum(r.get("minutes", 0) for r in recent if r.get("agent") == a) for a in AGENTS}
    plan = []
    for w in wos:
        if only_agent:
            agent, reason = only_agent, "forced with --agent"
        elif str(w.get("assignee", "either")).lower() in AGENTS:
            agent, reason = choose_agent(w, cfg)
        else:
            avail = [a for a in AGENTS if not in_cooldown(a, cfg)]
            if not avail:
                agent, reason = None, "both agents are rate-limited"
            else:
                total = sum(tally.values()) or 1
                agent = max(avail, key=lambda a: cfg["target_split"].get(a, 0) - tally[a] / total)
                reason = "balancing across this batch"
        if agent:
            tally[agent] += est.get(str(w.get("size", "M")), 25)
        plan.append((w, agent, reason))

    def job(item):
        w, agent, reason = item
        if agent is None:
            return {"wo": w.id, "skipped": reason}
        with sems[agent]:
            return dispatch(w.id, agent, dry_run, reason)

    results = []
    with cf.ThreadPoolExecutor(max_workers=sum(cfg["max_parallel"].values())) as ex:
        for fut in cf.as_completed([ex.submit(job, item) for item in plan]):
            results.append(fut.result())
    return results


def review(wo_id: str, agent_override=None, dry_run=False) -> dict:
    cfg = load_config()
    wo = find_wo(wo_id)
    built_by = str(wo.get("last_agent", "")).lower()
    agent = agent_override or next((a for a in AGENTS if a != built_by), "codex")
    path = worktree_root(cfg) / wo.id
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = runs_dir() / wo.id / f"{stamp}-review-{agent}"
    last_msg = run_dir / "last_message.md"
    acfg = cfg["agents"][agent]
    cmd = render(acfg["review"], last_message_file=str(last_msg))
    if dry_run:
        return {"wo": wo.id, "reviewer": agent, "cmd": cmd}
    if not path.exists():
        sys.exit(f"wo.py: no worktree for {wo.id}; dispatch it first.")
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt("review-prompt.md", wo, str(wo.get("branch", f"wo/{wo.id}")))
    t0 = time.time()
    res = subprocess.run(cmd, cwd=path, input=prompt, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=cfg["timeout_minutes"] * 60)
    (run_dir / "stdout.log").write_text(res.stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(res.stderr, encoding="utf-8")
    usage = parse_usage(acfg.get("output", ""), res.stdout, last_msg)
    minutes = round((time.time() - t0) / 60, 2)
    write_ledger({"ts": time.time(), "kind": "review", "wo": wo.id, "agent": agent,
                  "exit": res.returncode, "minutes": minutes,
                  **{k: v for k, v in usage.items() if k != "result"}})
    return {"wo": wo.id, "reviewer": agent, "exit": res.returncode,
            "review_file": str(last_msg.relative_to(ROOT))}


# --------------------------------------------------------------------------- simple commands

def cmd_init():
    for d in ("work-orders", "reports", "templates", "runs"):
        (orch() / d).mkdir(parents=True, exist_ok=True)
    gi = ROOT / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    for entry in ("orchestration/runs/", ".wo-test-output.txt"):
        if entry not in lines:
            lines.append(entry)
    gi.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Initialized orchestration/ and .gitignore entries.")


def cmd_new(title, assignee, size, phase, depends, gpu):
    existing = [int(m.group(1)) for p in wo_dir().glob("WO-*.md")
                if (m := re.match(r"WO-(\d+)", p.name))]
    n = max(existing, default=0) + 1
    wo_id = f"WO-{n:03d}"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    tpl = (orch() / "templates" / "work-order.md").read_text(encoding="utf-8")
    text = (tpl.replace("{id}", wo_id).replace("{title}", title).replace("{assignee}", assignee)
               .replace("{size}", size).replace("{phase}", str(phase))
               .replace("{depends_on}", ", ".join(depends)).replace("{gpu}", "true" if gpu else "false")
               .replace("{created}", dt.date.today().isoformat()))
    path = wo_dir() / f"{wo_id}-{slug}.md"
    path.write_text(text, encoding="utf-8")
    print(path.relative_to(ROOT))


def cmd_board():
    wos = all_wos()
    if not wos:
        print("No work orders yet.")
        return
    for status in STATUSES:
        group = [w for w in wos if w.get("status") == status]
        if not group:
            continue
        print(f"\n{status.upper()} ({len(group)})")
        for w in group:
            deps = w.get("depends_on", []) or []
            dep = f"  needs {', '.join(deps)}" if deps and status in ("draft", "ready") else ""
            print(f"  {w.id:8} {str(w.get('assignee', '?')):7} {str(w.get('size', '?')):2} "
                  f"P{w.get('phase', '?')}  {w.get('title', '')}{dep}")
    share = usage_share(load_config())
    print(f"\nRecent work share: " + ", ".join(f"{a} {share[a]:.0%}" for a in AGENTS))


def cmd_set(wo_id, pairs):
    def apply(w):
        for p in pairs:
            k, _, v = p.partition("=")
            if k == "status" and v not in STATUSES:
                sys.exit(f"wo.py: status must be one of {STATUSES}")
            w.set(k, _parse_value(v))
    w = update_wo(wo_id, apply)
    print(f"{w.id}: " + ", ".join(pairs))


def cmd_rework(wo_id, notes):
    def apply(w):
        if "## Rework notes" not in w.body:
            w.append_body("\n## Rework notes\n")
        w.append_body(f"- {now()}: {notes}\n")
        w.set("status", "rework")
    update_wo(wo_id, apply)
    print(f"{wo_id}: sent back for rework")


def cmd_merge(wo_id):
    cfg = load_config()
    wo = find_wo(wo_id)
    branch = wo.get("branch") or f"wo/{wo.id}"
    current = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if current != cfg["main_branch"]:
        sys.exit(f"wo.py: check out {cfg['main_branch']} first (you are on {current}).")
    dirty = [l for l in git("status", "--porcelain").stdout.splitlines()
             if "orchestration/work-orders/" not in l]
    if dirty:
        sys.exit("wo.py: main has uncommitted changes outside work-orders/; commit or stash them first.")
    git("merge", "--no-ff", branch, "-m", f"Merge {wo.id}: {wo.get('title', '')}")
    update_wo(wo.id, lambda w: w.set("status", "done"))
    cmd_cleanup(wo.id, delete_branch=True)
    print(f"{wo.id}: merged into {cfg['main_branch']} and cleaned up")


def cmd_cleanup(wo_id, delete_branch=False):
    cfg = load_config()
    wo = find_wo(wo_id)
    path = worktree_root(cfg) / wo.id
    if path.exists():
        git("worktree", "remove", "--force", str(path))
    git("worktree", "prune", check=False)
    if delete_branch:
        git("branch", "-D", wo.get("branch") or f"wo/{wo.id}", check=False)


def cmd_ledger():
    cfg = load_config()
    rows = read_ledger()
    if not rows:
        print("Ledger is empty.")
        return
    print(f"{'agent':8}{'kind':8}{'runs':>6}{'minutes':>10}{'tokens in':>12}{'tokens out':>12}{'cost $':>9}{'429s':>6}")
    for a in AGENTS:
        for kind in ("work", "review"):
            rs = [r for r in rows if r.get("agent") == a and r.get("kind") == kind]
            if not rs:
                continue
            tin = sum(r.get("input_tokens") or 0 for r in rs)
            tout = sum(r.get("output_tokens") or 0 for r in rs)
            cost = sum(r.get("cost_usd") or 0 for r in rs)
            print(f"{a:8}{kind:8}{len(rs):>6}{sum(r.get('minutes', 0) for r in rs):>10.1f}"
                  f"{tin:>12,}{tout:>12,}{cost:>9.2f}{sum(1 for r in rs if r.get('rate_limited')):>6}")
    share = usage_share(cfg)
    print("\nLast {} work runs, share of agent minutes vs target:".format(cfg["balance_window_runs"]))
    for a in AGENTS:
        print(f"  {a:7} {share[a]:>5.0%}  (target {cfg['target_split'].get(a, 0):.0%})"
              + ("  [cooling down]" if in_cooldown(a, cfg) else ""))


# --------------------------------------------------------------------------- CLI

def main(argv=None):
    global ROOT
    ROOT = repo_root()
    ap = argparse.ArgumentParser(prog="wo.py", description="Work-order dispatcher")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p = sub.add_parser("new")
    p.add_argument("title")
    p.add_argument("--assignee", default="either", choices=["codex", "claude", "either"])
    p.add_argument("--size", default="M", choices=["S", "M", "L"])
    p.add_argument("--phase", default="0")
    p.add_argument("--depends", nargs="*", default=[])
    p.add_argument("--gpu", action="store_true")
    sub.add_parser("board")
    p = sub.add_parser("show"); p.add_argument("id")
    p = sub.add_parser("set"); p.add_argument("id"); p.add_argument("pairs", nargs="+")
    p = sub.add_parser("dispatch"); p.add_argument("id"); p.add_argument("--agent", choices=AGENTS)
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("run-ready"); p.add_argument("--max", type=int)
    p.add_argument("--agent", choices=AGENTS); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("review"); p.add_argument("id"); p.add_argument("--agent", choices=AGENTS)
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("rework"); p.add_argument("id"); p.add_argument("notes")
    p = sub.add_parser("merge"); p.add_argument("id")
    p = sub.add_parser("cleanup"); p.add_argument("id"); p.add_argument("--delete-branch", action="store_true")
    sub.add_parser("ledger")
    a = ap.parse_args(argv)

    if a.cmd == "init":
        cmd_init()
    elif a.cmd == "new":
        cmd_new(a.title, a.assignee, a.size, a.phase, a.depends, a.gpu)
    elif a.cmd == "board":
        cmd_board()
    elif a.cmd == "show":
        print(find_wo(a.id).path.read_text(encoding="utf-8"))
    elif a.cmd == "set":
        cmd_set(a.id, a.pairs)
    elif a.cmd == "dispatch":
        print(json.dumps(dispatch(a.id, a.agent, a.dry_run), indent=2))
    elif a.cmd == "run-ready":
        print(json.dumps(run_ready(a.max, a.dry_run, a.agent), indent=2))
    elif a.cmd == "review":
        print(json.dumps(review(a.id, a.agent, a.dry_run), indent=2))
    elif a.cmd == "rework":
        cmd_rework(a.id, a.notes)
    elif a.cmd == "merge":
        cmd_merge(a.id)
    elif a.cmd == "cleanup":
        cmd_cleanup(a.id, a.delete_branch)
    elif a.cmd == "ledger":
        cmd_ledger()


if __name__ == "__main__":
    main()
