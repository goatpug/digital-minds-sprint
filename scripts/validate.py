#!/usr/bin/env python3
"""Consistency and leak checks. Run before judging and again before scoring.

    python3 scripts/validate.py

Checks:
- every non-placeholder prompt has a well-formed responses file (5 responses,
  exactly one target, canary has none)
- lineups exist, letters complete, and contain NO term from the redaction list
  (leak scan of prompt+option text)
- leak scan of everything else a judge can see: redacted corpus/*.md,
  profiles/style_profile.md, and every built packet in packets/*/
- judging files parse, ids match a lineup, picks are legal letters/NONE
- Sharon-blinding sanity: keys/ files are base64, not plaintext JSON
"""
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LETTERS = {"A", "B", "C", "D", "E"}
problems = []
warnings = []


def check(cond, msg, warn=False):
    if not cond:
        (warnings if warn else problems).append(msg)


def leak_terms():
    """Two tiers: named terms are hard leaks (fail); version-number patterns are
    high-recall/low-precision ('4.5 hours' is innocent prose), so their hits are
    inspect-manually warnings — never blanket-fix them with redact.py --write."""
    cfg = json.loads((ROOT / "scripts" / "redact_config.json").read_text())
    terms = [t for t in cfg["replacements"] if t.lower() not in {"sonnet", "opus"}]  # family names alone over-trigger
    term_rxs = [re.compile(re.escape(t), re.IGNORECASE) for t in terms]
    pat_rxs = [re.compile(p, re.IGNORECASE) for p in cfg.get("patterns", [])]
    # bare family names are warn-tier: redact.py replaces them, but if redaction were
    # ever skipped they'd otherwise pass silently, and "Sonnet" narrows the lineup
    pat_rxs += [re.compile(r"\bsonnet\b", re.IGNORECASE), re.compile(r"\bopus\b", re.IGNORECASE)]
    return term_rxs, pat_rxs


def leak_scan(label, text, term_rxs, pat_rxs):
    for rx in term_rxs:
        m = rx.search(text)
        check(not m, f"{label}: LEAK — '{m.group(0) if m else ''}' matches redaction list. "
                     "Run redact.py --write and reassemble.")
    for rx in pat_rxs:
        m = rx.search(text)
        check(not m, f"{label}: soft hit '{m.group(0) if m else ''}' — inspect manually "
                     "(bare versions/family names can be innocent prose; do NOT blanket redact.py --write)", warn=True)


def main():
    prompts = {p["id"]: p for p in json.loads((ROOT / "prompts" / "prompts.json").read_text())["prompts"]}

    # responses
    for pid, p in prompts.items():
        if p.get("repeat_of"):
            continue
        path = ROOT / "responses" / f"{pid}.json"
        if not path.exists():
            check(False, f"responses/{pid}.json missing (ok if not collected yet)", warn=True)
            continue
        data = json.loads(path.read_text())
        check(data.get("prompt_id") == pid, f"responses/{pid}.json: prompt_id mismatch")
        rs = data.get("responses", [])
        check(len(rs) == 5, f"responses/{pid}.json: {len(rs)} responses, need 5")
        n_target = sum(1 for r in rs if r.get("is_target"))
        if p.get("canary"):
            check(n_target == 0, f"responses/{pid}.json: canary must have zero is_target, has {n_target}")
        else:
            check(n_target == 1, f"responses/{pid}.json: need exactly one is_target, has {n_target}")
        check(all(r.get("text", "").strip() for r in rs), f"responses/{pid}.json: empty text field")

    # lineups + leak scan
    term_rxs, pat_rxs = leak_terms()
    for lp in sorted((ROOT / "lineups").glob("P*.json")):
        lineup = json.loads(lp.read_text())
        letters = {o["letter"] for o in lineup.get("options", [])}
        check(letters == LETTERS, f"{lp.name}: letters {letters} != A-E")
        blob = lineup.get("prompt_text", "") + " " + " ".join(o["text"] for o in lineup["options"])
        leak_scan(lp.name, blob, term_rxs, pat_rxs)

    # leak scan of everything else judge-visible: corpus, style profile, built packets
    judge_visible = sorted((ROOT / "corpus").glob("*.md")) + sorted((ROOT / "packets").glob("*/P*.md"))
    profile = ROOT / "profiles" / "style_profile.md"
    if profile.exists():
        judge_visible.append(profile)
    for fp in judge_visible:
        leak_scan(str(fp.relative_to(ROOT)), fp.read_text(), term_rxs, pat_rxs)

    # attunement-first ordering (PROTOCOL §4 / D10): warn if AI judgments exist
    # while Sharon's attunement trials are incomplete
    filed = [jp.stem.split("__") for jp in (ROOT / "judging").glob("*.json")]
    ai_filed = [p for p in filed if len(p) == 3 and p[0] != "sharon"]
    if ai_filed:
        repeats = {lp.stem for lp in (ROOT / "lineups").glob("P*.json")
                   if json.loads(lp.read_text()).get("repeat_of")}
        for pk in sorted((ROOT / "packets" / "attunement").glob("P*.md")):
            if pk.stem not in repeats and ["sharon", "attunement", pk.stem] not in filed:
                check(False, f"AI judgments filed but sharon__attunement__{pk.stem} is missing — "
                             "attunement-first ordering (§4/D10) may have been violated", warn=True)

    # keys are blinded
    for kp in sorted((ROOT / "keys").glob("P*.key")):
        raw = kp.read_text().strip()
        check(not raw.startswith("{"), f"{kp.name}: key is PLAINTEXT — Sharon-blinding broken")
        try:
            json.loads(base64.b64decode(raw))
        except Exception:
            check(False, f"{kp.name}: key does not decode to JSON")

    # judging files
    for jp in sorted((ROOT / "judging").glob("*.json")):
        try:
            j = json.loads(jp.read_text())
        except Exception as e:
            check(False, f"{jp.name}: unparseable ({e})")
            continue
        parts = jp.stem.split("__")
        check(len(parts) == 3, f"{jp.name}: name must be judge__arm__promptid.json")
        if len(parts) == 3:
            check(j.get("judge") == parts[0] and j.get("arm") == parts[1] and j.get("prompt_id") == parts[2],
                  f"{jp.name}: filename/content mismatch")
            check((ROOT / "lineups" / f"{parts[2]}.json").exists(), f"{jp.name}: no such lineup {parts[2]}")
        pick = j.get("pick")
        check(pick in LETTERS or pick == "NONE", f"{jp.name}: illegal pick {pick!r}")
        conf = j.get("confidence")
        check(isinstance(conf, (int, float)) and 0 <= conf <= 100, f"{jp.name}: confidence {conf!r} not in 0-100")

    for w in warnings:
        print(f"  warn: {w}")
    if problems:
        print("\nFAIL:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"\nOK — no blocking problems ({len(warnings)} warning(s)).")


if __name__ == "__main__":
    main()
