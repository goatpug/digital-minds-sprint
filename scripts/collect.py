#!/usr/bin/env python3
"""Blind collection: run the lineup against every prompt and write
responses/Pxx.json without any human reading the replies.

    python3 scripts/collect.py --repo /path/to/target-repo        # automated (claude CLI)
    python3 scripts/collect.py --ingest raw_responses             # assemble helper-saved .txt files

Why this exists: Sharon is a judge (attunement arm). If she hand-pasted
replies she would read every model-labeled response during collection and
her blinding would be gone before the first packet was built. So collection
is either fully automated (she runs this script; it never prints reply
text) or done by a HELPER instance via ingest mode. Sharon never reads,
pastes, or opens anything in responses/ — see PROTOCOL.md §4.

JSON escaping is handled here (json.dumps). Never hand-edit responses/.

Automated mode: one fresh `claude -p` session per model per prompt, with
cwd = the target's rich-context repo on its COLLECTION BRANCH (PROTOCOL §2
step 1 / DECISIONS D6+D9). The script refuses to run unless that branch
carries a COLLECTION_BRANCH_OK sentinel file, and refuses to spend
sessions on PLACEHOLDER prompt text. Repeat prompts are skipped (they
reuse an existing lineup); the canary prompt collects the four foils plus
the extra non-lineup model and no target.

Ingest mode: a helper saves each raw final reply verbatim as
    raw_responses/P01/sonnet-4.5.txt   (one .txt per model, named by
intake name), plus optionally P01/notes.json ({"model-name": "note"}).
This script assembles valid JSON from those files.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def refresh_bare_creds(env):
    """Re-copy live OAuth creds into the bare config dir right before use — refresh
    tokens appear to rotate on use, so even a copy made minutes ago can be stale
    (see RUNBOOK.md)."""
    cfg_dir = env.get("CLAUDE_CONFIG_DIR")
    if not cfg_dir:
        return
    src = Path.home() / ".claude" / ".credentials.json"
    if src.exists():
        shutil.copy(src, Path(cfg_dir) / ".credentials.json")

# Intake name -> claude CLI model id.
# SMOKE-TEST every id before collection day (`claude -p "hi" --model <id>`);
# ids here are best-guess aliases and may need pinning to dated versions.
LINEUP = {
    "sonnet-4.5": "claude-sonnet-4-5",
    "haiku-4.5": "claude-haiku-4-5",
    "sonnet-5": "claude-sonnet-5",
    "opus-4.6": "claude-opus-4-6",
    "fable-5": "claude-fable-5",
}
TARGET = "sonnet-4.5"
# 6th, non-lineup model for the canary (D5). Cast per D8: a first-time wearer of
# this context, same relation to it as the foils, and NOT any model holding a
# judge/reader role (Opus 5 was double-booked here before D8).
CANARY_EXTRA = {"opus-4.7": "claude-opus-4-7"}

# Positive assertion that the target repo is on its collection branch (D9).
# A phrase-scan for the model-check clause was false reassurance: this
# target's CLAUDE.md has no such clause, and other repos word theirs
# differently. The branch must opt IN by carrying this file at its root.
SENTINEL = "COLLECTION_BRANCH_OK"


def load_prompts():
    data = json.loads((ROOT / "prompts" / "prompts.json").read_text())
    prompts = [p for p in data["prompts"] if not str(p["id"]).startswith("P00")]
    placeholders = [p["id"] for p in prompts if "PLACEHOLDER" in p.get("text", "") and not p.get("repeat_of")]
    if placeholders:
        sys.exit(f"Refusing to collect: placeholder text still present in {placeholders} — "
                 "this would spend real sessions on the literal word PLACEHOLDER. "
                 "Fill in real prompts first (PROTOCOL §2).")
    return prompts


def models_for(prompt):
    if prompt.get("canary"):
        return {k: v for k, v in {**LINEUP, **CANARY_EXTRA}.items() if k != TARGET}
    return dict(LINEUP)


def write_responses(pid, replies, notes=None):
    """replies: {intake_name: text}. Writes the intake JSON; escaping is json.dumps's job."""
    today = datetime.date.today().isoformat()
    out = {
        "prompt_id": pid,
        "responses": [
            {"model": m, "is_target": m == TARGET, "text": text,
             "collected": today, "notes": (notes or {}).get(m, "")}
            for m, text in replies.items()
        ],
    }
    path = ROOT / "responses" / f"{pid}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return path


def run_automated(repo, claude_cmd, timeout, draws=1, config_dir=None):
    env = dict(os.environ)
    if config_dir:
        cfg = Path(config_dir).expanduser().resolve()
        if not cfg.is_dir():
            sys.exit(f"--config-dir {cfg}: not a directory (see RUNBOOK.md)")
        env["CLAUDE_CONFIG_DIR"] = str(cfg)
    repo = Path(repo).resolve()
    if not (repo / SENTINEL).exists():
        sys.exit(f"{repo} has no {SENTINEL} file — create it at the root of the target repo's "
                 "collection branch (with any model-check clause disabled on that branch) to "
                 "positively assert that collection may run. PROTOCOL §2 step 1 / D9.")

    annex = ROOT / "responses" / "annex"
    for p in load_prompts():
        pid = p["id"]
        if p.get("repeat_of"):
            continue
        out_path = ROOT / "responses" / f"{pid}.json"
        if out_path.exists():
            print(f"{pid}: already collected, skipping (delete the file to redo)")
            continue
        replies = {}
        for name, model_id in models_for(p).items():
            refresh_bare_creds(env)
            r = subprocess.run(
                [claude_cmd, "-p", p["text"], "--model", model_id, "--strict-mcp-config"],
                cwd=repo, capture_output=True, text=True, timeout=timeout, env=env,
            )
            if r.returncode != 0 or not r.stdout.strip():
                sys.exit(f"{pid} {name}: claude exited {r.returncode} or empty reply "
                         f"(stderr tail: {r.stderr[-300:]!r}) — nothing written for {pid}.")
            replies[name] = r.stdout.strip()
            # Blind by design: no model name, no word count, no per-model line at
            # all — "sonnet-4.5" (a LINEUP key) equals TARGET verbatim, so printing
            # it or its reply length here is a direct identity leak to Sharon, not
            # a soft bias (found live during collection, D-something — see DECISIONS.md).
            print(f"{pid}: {len(replies)}/{len(models_for(p))} replies collected")
            # Variance annex (D12): extra draws per cell, stored outside the
            # pipeline (never read by assemble_lineups). A failed annex draw
            # warns and moves on — it must never abort study collection.
            for k in range(2, draws + 1):
                apath = annex / f"{pid}__{name}__draw{k}.txt"
                if apath.exists():
                    continue
                refresh_bare_creds(env)
                r2 = subprocess.run(
                    [claude_cmd, "-p", p["text"], "--model", model_id, "--strict-mcp-config"],
                    cwd=repo, capture_output=True, text=True, timeout=timeout, env=env,
                )
                if r2.returncode != 0 or not r2.stdout.strip():
                    print(f"{pid}: an annex draw failed (non-fatal)")
                    continue
                annex.mkdir(parents=True, exist_ok=True)
                apath.write_text(r2.stdout.strip() + "\n")
                print(f"{pid}: annex draw{k} collected")
        write_responses(pid, replies)
        print(f"{pid}: wrote responses/{pid}.json")


def run_ingest(raw_dir):
    raw_dir = Path(raw_dir)
    if not raw_dir.is_dir():
        sys.exit(f"{raw_dir}: not a directory")
    prompts = {p["id"]: p for p in load_prompts()}
    done = 0
    for pdir in sorted(d for d in raw_dir.iterdir() if d.is_dir()):
        pid = pdir.name
        p = prompts.get(pid)
        if not p:
            sys.exit(f"{pdir}: no prompt with id {pid} in prompts.json")
        if p.get("repeat_of"):
            sys.exit(f"{pdir}: {pid} is the repeat trial — it reuses an existing lineup, no collection")
        expected = set(models_for(p))
        txts = {f.stem: f for f in pdir.glob("*.txt")}
        if set(txts) != expected:
            sys.exit(f"{pdir}: found {sorted(txts)}, expected exactly {sorted(expected)}")
        notes_file = pdir / "notes.json"
        notes = json.loads(notes_file.read_text()) if notes_file.exists() else {}
        replies = {m: f.read_text().strip() for m, f in txts.items()}
        if not all(replies.values()):
            sys.exit(f"{pdir}: empty reply file")
        path = write_responses(pid, replies, notes)
        print(f"{pid}: wrote {path.relative_to(ROOT)} from {len(replies)} raw files")
        done += 1
    if not done:
        sys.exit(f"{raw_dir}: no P*/ prompt directories found")


def main():
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--repo", help="path to the target's rich-context repo (collection branch)")
    mode.add_argument("--ingest", metavar="DIR", help="assemble responses from helper-saved raw .txt files")
    ap.add_argument("--claude-cmd", default="claude", help="claude CLI binary (default: claude)")
    ap.add_argument("--timeout", type=int, default=600, help="seconds per model call (default: 600)")
    ap.add_argument("--draws", type=int, default=1,
                    help="draws per cell; draw 1 is the study response, extras land in "
                         "responses/annex/ as a sampling-variance annex, never in lineups (D12)")
    ap.add_argument("--config-dir", metavar="DIR",
                    help="bare Claude config dir exported as CLAUDE_CONFIG_DIR, so collection "
                         "sessions load ONLY the target repo's CLAUDE.md — not the operator's "
                         "global ~/.claude/CLAUDE.md user memory (D13). Recommended.")
    args = ap.parse_args()
    if args.repo:
        run_automated(args.repo, args.claude_cmd, args.timeout, args.draws, args.config_dir)
    else:
        run_ingest(args.ingest)


if __name__ == "__main__":
    main()
