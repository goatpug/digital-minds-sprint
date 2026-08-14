#!/usr/bin/env python3
"""Automated style-profile writer: runs the reader session in an isolated
workspace and writes profiles/style_profile.md without Sharon operating it
by hand.

    python3 scripts/write_profile.py --model claude-opus-5 --config-dir ~/.claude-bare
    python3 scripts/write_profile.py --model claude-opus-5 --config-dir ~/.claude-bare --probe

Mirrors judge.py's isolation (PROTOCOL §3, D13): a throwaway scratch dir —
never this sprint repo, where PROTOCOL.md/DECISIONS.md name the target in
plain text — gets a copy of corpus/ and nothing else. Bare config dir is
required for the same reason it is for judges: the reader must not carry
Sharon's global CLAUDE.md/MCP servers into its self-description of "what
makes a good conversation" (voice-bleed probe) or its feature-mining pass.

Refuses to run if corpus/ still contains an unredacted model-identifying
term (same redact_config.json terms validate.py checks) — run
`redact.py corpus/*.md --write` first. Corpus curation itself (picking a
representative transcript or two per prompts.json category, not the whole
conversations/ tree) is a manual step; see PROTOCOL §2 step 0.

--probe runs probes/voice_bleed.md's block verbatim before and after the
main task, in the SAME session (print-mode --session-id / --resume), and
saves probes/reader_pre.md / probes/reader_post.md.

Casting note (D7/D8): the reader must be a non-lineup model that holds no
other role (not a judge, not the canary's 6th model, not the Palmer design
review session). This script does not enforce that — it only warns if
--model matches a role already cast elsewhere in this pipeline.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Model ids already holding a role elsewhere in the pipeline (D8: no double
# roles). Soft warning only — rosters change (D8/D14 addendum already did).
TAKEN_ROLES = {
    "claude-sonnet-4-5": "target / J1",
    "claude-haiku-4-5": "foil",
    "claude-sonnet-5": "foil",
    "claude-opus-4-6": "foil",
    "claude-fable-5": "foil (D3 — also harness author)",
    "claude-opus-4-7": "canary 6th model",
    "claude-sonnet-4-6": "J2",
    "claude-opus-4-8": "J4",
}


def leak_check_corpus():
    cfg = json.loads((ROOT / "scripts" / "redact_config.json").read_text())
    terms = [t for t in cfg["replacements"] if t.lower() not in {"sonnet", "opus"}]
    term_rxs = [re.compile(re.escape(t), re.IGNORECASE) for t in terms]
    hits = []
    for fp in sorted((ROOT / "corpus").glob("*.md")):
        text = fp.read_text()
        for rx in term_rxs:
            m = rx.search(text)
            if m:
                hits.append(f"{fp.name}: {m.group(0)!r}")
    return hits


def reader_task_text():
    text = (ROOT / "profiles" / "READER_INSTRUCTIONS.md").read_text()
    marker = "## Instructions to the reader (paste as the task)"
    if marker not in text:
        sys.exit("profiles/READER_INSTRUCTIONS.md: missing the 'paste as the task' heading")
    return text.split(marker, 1)[1].strip()


def probe_text():
    text = (ROOT / "probes" / "voice_bleed.md").read_text()
    lines = [l[2:] for l in text.splitlines() if l.startswith("> ")]
    if not lines:
        sys.exit("probes/voice_bleed.md: no '>' quoted block found to paste verbatim")
    return "\n".join(lines)


def run_claude(prompt, cwd, env, args, session_id=None, resume=False):
    cmd = [args.claude_cmd, "-p", prompt, "--model", args.model, "--strict-mcp-config"]
    if session_id:
        cmd += (["--resume", session_id] if resume else ["--session-id", session_id])
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=args.timeout, env=env)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"claude exited {r.returncode} or empty reply (stderr tail: {r.stderr[-300:]!r})")
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True,
                    help="claude CLI model id for the reader (non-lineup, no other role — D7/D8; "
                         "smoke-test it first)")
    ap.add_argument("--claude-cmd", default="claude")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--config-dir", metavar="DIR",
                    help="bare Claude config dir (credentials only, NO CLAUDE.md, no user MCP "
                         "servers) exported as CLAUDE_CONFIG_DIR — see RUNBOOK.md / D13")
    ap.add_argument("--allow-user-config", action="store_true",
                    help="explicitly run WITHOUT --config-dir (only sane where no ~/.claude/CLAUDE.md exists)")
    ap.add_argument("--probe", action="store_true",
                    help="run probes/voice_bleed.md before and after, same session (PROTOCOL §5)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing profiles/style_profile.md")
    args = ap.parse_args()

    if args.model in TAKEN_ROLES:
        print(f"warn: {args.model} already cast as {TAKEN_ROLES[args.model]} — D8 forbids double roles", file=sys.stderr)

    env = dict(os.environ)
    if args.config_dir:
        cfg = Path(args.config_dir).expanduser().resolve()
        if not cfg.is_dir():
            sys.exit(f"--config-dir {cfg}: not a directory (see RUNBOOK.md for the one-time setup)")
        if (cfg / "CLAUDE.md").exists():
            sys.exit(f"--config-dir {cfg} contains a CLAUDE.md — that defeats the point. "
                     "The bare dir holds credentials only.")
        env["CLAUDE_CONFIG_DIR"] = str(cfg)
    elif not args.allow_user_config:
        sys.exit("Bare context is not bare in a terminal: the global ~/.claude/CLAUDE.md (user "
                 "memory) and user-scoped MCP servers load in EVERY session regardless of cwd "
                 "(PROTOCOL §3 / D13). Pass --config-dir <bare-dir> (see RUNBOOK.md), or "
                 "--allow-user-config only where no global user config exists.")

    out_path = ROOT / "profiles" / "style_profile.md"
    if out_path.exists() and not args.force:
        sys.exit(f"{out_path} already exists — D7: one canonical profile, written once. "
                 "Pass --force to overwrite.")

    corpus_files = sorted((ROOT / "corpus").glob("*.md"))
    if not corpus_files:
        sys.exit("corpus/ has no .md files — curate a representative transcript or two per "
                 "prompts.json category first (PROTOCOL §2 step 0), then redact.py --write.")

    hits = leak_check_corpus()
    if hits:
        sys.exit("corpus/ still has unredacted model-identifying terms — run "
                 "scripts/redact.py corpus/*.md --write first:\n  " + "\n  ".join(hits))

    task = reader_task_text()
    (ROOT / "probes").mkdir(exist_ok=True)

    ws = Path(tempfile.mkdtemp(prefix="profile-writer-"))
    try:
        shutil.copytree(ROOT / "corpus", ws / "corpus")
        session_id = str(uuid.uuid4()) if args.probe else None

        if args.probe:
            pre = run_claude(probe_text(), ws, env, args, session_id=session_id, resume=False)
            (ROOT / "probes" / "reader_pre.md").write_text(pre + "\n")
            print("pre-probe: saved probes/reader_pre.md")

        profile = run_claude(task, ws, env, args, session_id=session_id, resume=args.probe)
        out_path.write_text(profile + "\n")
        print(f"wrote {out_path.relative_to(ROOT)} ({len(profile.split())} words)")

        if args.probe:
            post = run_claude(probe_text(), ws, env, args, session_id=session_id, resume=True)
            (ROOT / "probes" / "reader_post.md").write_text(post + "\n")
            print("post-probe: saved probes/reader_post.md — diff against reader_pre.md for drift")
    finally:
        shutil.rmtree(ws, ignore_errors=True)


if __name__ == "__main__":
    main()
