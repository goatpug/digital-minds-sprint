#!/usr/bin/env python3
"""Redact model-identifying terms from corpus/response files.

Usage:
    python3 scripts/redact.py responses/*.json corpus/*.md          # dry run, report only
    python3 scripts/redact.py responses/*.json corpus/*.md --write  # apply in place

Replacements come from scripts/redact_config.json. In responses/*.json only the
"text" fields are touched — the "model"/"is_target" bookkeeping fields stay intact
(they never leave that directory; lineups are letters-only).

Version-number patterns apply to corpus .md files ONLY: in conversational
responses a bare "4.5" is usually innocent prose ("about 4.5 hours"), and
rewriting it to [REDACTED-VERSION] would silently corrupt a legitimate reply.
validate.py flags pattern hits in responses/lineups for manual inspection.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "redact_config.json").read_text())


def build_rules():
    terms = [(re.compile(re.escape(t), re.IGNORECASE), repl)
             for t, repl in sorted(CONFIG["replacements"].items(), key=lambda kv: -len(kv[0]))]
    pats = [(re.compile(p, re.IGNORECASE), "[REDACTED-VERSION]") for p in CONFIG.get("patterns", [])]
    return terms, pats


def redact_text(text, rules):
    count = 0
    for rx, repl in rules:
        text, n = rx.subn(repl, text)
        count += n
    return text, count


def main():
    args = [a for a in sys.argv[1:] if a != "--write"]
    write = "--write" in sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    terms, pats = build_rules()
    total = 0
    for name in args:
        path = Path(name)
        raw = path.read_text()
        if path.suffix == ".json":
            data = json.loads(raw)
            count = 0
            for resp in data.get("responses", []):
                resp["text"], n = redact_text(resp["text"], terms)  # terms only — see docstring
                count += n
                resp["notes"], n = redact_text(resp.get("notes", ""), terms)
                count += n
            out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        else:
            out, count = redact_text(raw, terms + pats)
        total += count
        status = "WROTE" if (write and count) else ("would redact" if count else "clean")
        print(f"{path}: {count} replacement(s) [{status}]")
        if write and count:
            path.write_text(out)
    print(f"\nTotal: {total} replacement(s). {'Applied.' if write else 'DRY RUN — rerun with --write to apply.'}")


if __name__ == "__main__":
    main()
