#!/usr/bin/env python3
"""Automated blind judging: run AI judge sessions in isolated workspaces and
file their JSON replies without any human reading them.

    python3 scripts/judge.py --judge sonnet-4.6 --model claude-sonnet-4-6 --arm untrained
    python3 scripts/judge.py --judge sonnet-4.6 --model claude-sonnet-4-6 --arm raw

Closes two protocol holes at once (PROTOCOL §3/§4, DECISIONS D10):

- Judge workspace: each session runs in a throwaway scratch directory, never
  in this sprint repo — where PROTOCOL.md, DECISIONS.md (which names the
  target in plain text), responses/ and keys/ are one `ls` away, and base64
  is not a blindfold against a model that can run `base64 -d`. The scratch
  dir contains nothing; for the raw arm it gets a copy of redacted corpus/.

- Human transport: replies are parsed and filed by code. Judge JSON contains
  picks and verbatim-quoted reasons; Sharon (attunement judge) must never
  read one. This script prints only per-trial checkmarks, and refuses to run
  at all until every attunement trial is filed (§4 ordering rule) — override
  with --pilot ONLY for synthetic pipeline tests, never for study data.

Repeat trials need a session that already judged the original, which a
single `claude -p` cannot be; they are skipped here (contamination is
prevented rather than measured — PROTOCOL §2 step 6). Sharon still takes
her own repeat trial manually.

If a judge breaks the response format, the raw reply is saved to
judging/failed/ for a HELPER instance (not Sharon) to transcribe per
judging/README.md.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LETTERS = {"A", "B", "C", "D", "E"}


def repeat_ids():
    out = {}
    for lp in (ROOT / "lineups").glob("P*.json"):
        r = json.loads(lp.read_text()).get("repeat_of")
        if r:
            out[lp.stem] = r
    return out


def attunement_gap(repeats):
    """Attunement trials not yet filed (repeat excluded — Sharon may take it last)."""
    missing = []
    for pk in sorted((ROOT / "packets" / "attunement").glob("P*.md")):
        pid = pk.stem
        if pid in repeats:
            continue
        if not (ROOT / "judging" / f"sharon__attunement__{pid}.json").exists():
            missing.append(pid)
    return missing


def extract_json(text):
    """First ```json fence, else first parseable {...} in the text."""
    if "```json" in text:
        candidate = text.split("```json", 1)[1].split("```", 1)[0]
        return json.loads(candidate)
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text[i:])
                return obj
            except ValueError:
                continue
    raise ValueError("no JSON object found in reply")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True, help="intake name for filenames/JSON (e.g. sonnet-4.6)")
    ap.add_argument("--model", required=True, help="claude CLI model id (smoke-test it first)")
    ap.add_argument("--arm", required=True, choices=["untrained", "profile", "raw"])
    ap.add_argument("--claude-cmd", default="claude")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--config-dir", metavar="DIR",
                    help="bare Claude config dir (credentials only, NO CLAUDE.md, no user MCP "
                         "servers) exported as CLAUDE_CONFIG_DIR so the judge session loads no "
                         "global user memory — see RUNBOOK.md / D13")
    ap.add_argument("--allow-user-config", action="store_true",
                    help="explicitly run WITHOUT --config-dir (only sane where no ~/.claude/CLAUDE.md "
                         "exists, e.g. a clean container)")
    ap.add_argument("--pilot", action="store_true",
                    help="skip the attunement-first check — synthetic pipeline tests ONLY")
    args = ap.parse_args()

    if args.judge == "sharon":
        sys.exit("Sharon judges the attunement packets herself — this script is for AI judges only.")

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
                 "memory) and user-scoped MCP servers load in EVERY session regardless of cwd, "
                 "so a judge could carry Sharon's preferences and reach the memory server "
                 "(PROTOCOL §3 / D13). Pass --config-dir <bare-dir> (see RUNBOOK.md), or "
                 "--allow-user-config only where no global user config exists.")

    repeats = repeat_ids()
    if not args.pilot:
        missing = attunement_gap(repeats)
        if missing:
            sys.exit("Attunement arm incomplete — Sharon must file ALL her trials before any AI judge "
                     f"session runs (PROTOCOL §4 / D10). Missing: {', '.join(missing)}")

    packets = sorted((ROOT / "packets" / args.arm).glob("P*.md"))
    if not packets:
        sys.exit(f"No packets in packets/{args.arm}/ — run build_packets.py first.")
    (ROOT / "judging").mkdir(exist_ok=True)

    for pk in packets:
        pid = pk.stem
        out_path = ROOT / "judging" / f"{args.judge}__{args.arm}__{pid}.json"
        if pid in repeats:
            print(f"{pid}: repeat trial — needs a continued session, skipped (PROTOCOL §2 step 6)")
            continue
        if out_path.exists():
            print(f"{pid}: already filed, skipping")
            continue

        ws = Path(tempfile.mkdtemp(prefix=f"judge-{args.judge}-{pid}-"))
        try:
            if args.arm == "raw":
                shutil.copytree(ROOT / "corpus", ws / "corpus")
            r = subprocess.run(
                [args.claude_cmd, "-p", pk.read_text(), "--model", args.model,
                 "--strict-mcp-config"],
                cwd=ws, capture_output=True, text=True, timeout=args.timeout, env=env,
            )
            if r.returncode != 0:
                sys.exit(f"{pid}: claude exited {r.returncode} (stderr tail: {r.stderr[-300:]!r})")
            try:
                j = extract_json(r.stdout)
            except ValueError:
                failed = ROOT / "judging" / "failed"
                failed.mkdir(exist_ok=True)
                (failed / f"{args.judge}__{args.arm}__{pid}.txt").write_text(r.stdout)
                print(f"{pid}: ✗ unparseable reply — raw saved to judging/failed/ for a HELPER "
                      "(not Sharon) to transcribe")
                continue
            note = str(j.get("format_note", "") or "")
            if j.get("arm") != args.arm or j.get("prompt_id") != pid:
                note = (note + " | " if note else "") + "arm/prompt_id echo missing or wrong; set by judge.py"
            j.update({"judge": args.judge, "arm": args.arm, "prompt_id": pid, "format_note": note})
            if j.get("pick") not in LETTERS | {"NONE"}:
                j["format_note"] += (" | " if j["format_note"] else "") + f"illegal pick filed as-is"
            out_path.write_text(json.dumps(j, indent=2, ensure_ascii=False) + "\n")
            print(f"{pid}: ✓ filed")  # never the pick, never the reasons
        finally:
            shutil.rmtree(ws, ignore_errors=True)


if __name__ == "__main__":
    main()
