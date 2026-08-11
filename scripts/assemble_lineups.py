#!/usr/bin/env python3
"""Assemble blinded lineups from prompts + responses.

    python3 scripts/assemble_lineups.py [--seed 17]

Reads  prompts/prompts.json and responses/Pxx.json
Writes lineups/Pxx.json   (letters + texts only, no model names)
       keys/Pxx.key       (base64-encoded answer key — Sharon never opens these)

Target letters are balanced across trials (each of A–E used as evenly as
possible), then foils are shuffled into the remaining slots. Everything is
deterministic from the seed, which is recorded in every key file.

Repeat trials (prompts with "repeat_of") reuse the original lineup verbatim
under the new id, so drift between the two judgments is measurable.
"""
import argparse
import base64
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LETTERS = ["A", "B", "C", "D", "E"]


def load_prompts():
    data = json.loads((ROOT / "prompts" / "prompts.json").read_text())
    prompts = [p for p in data["prompts"] if not str(p["id"]).startswith("P00")]
    placeholders = [p["id"] for p in prompts if "PLACEHOLDER" in p.get("text", "") and not p.get("repeat_of")]
    if placeholders:
        sys.exit(f"Refusing to assemble: placeholder text still present in {placeholders}. "
                 f"Fill in real prompts first (PROTOCOL.md §2).")
    by_id = {p["id"]: p for p in prompts}
    bad = [p["id"] for p in prompts if p.get("repeat_of") and by_id.get(p["repeat_of"], {}).get("canary")]
    if bad:
        sys.exit(f"{bad}: repeat_of points at the canary — a repeated canary would double-count in "
                 f"both the canary and drift metrics. Point it at a normal trial.")
    return prompts


def load_responses(pid):
    path = ROOT / "responses" / f"{pid}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if len(data["responses"]) != 5:
        sys.exit(f"{path}: expected exactly 5 responses, found {len(data['responses'])}.")
    return data["responses"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=17)  # obviously
    args = ap.parse_args()
    rng = random.Random(args.seed)

    prompts = load_prompts()
    (ROOT / "lineups").mkdir(exist_ok=True)
    (ROOT / "keys").mkdir(exist_ok=True)

    # Balanced target-letter schedule for non-canary, non-repeat trials.
    real = [p for p in prompts if not p.get("canary") and not p.get("repeat_of")]
    schedule = []
    while len(schedule) < len(real):
        block = LETTERS[:]
        rng.shuffle(block)
        schedule.extend(block)
    target_letter_for = {p["id"]: schedule[i] for i, p in enumerate(real)}

    built, skipped = 0, []
    for p in prompts:
        pid = p["id"]
        if p.get("repeat_of"):
            src = ROOT / "lineups" / f"{p['repeat_of']}.json"
            if not src.exists():
                skipped.append(pid)
                continue
            lineup = json.loads(src.read_text())
            lineup["prompt_id"] = pid
            lineup["repeat_of"] = p["repeat_of"]
            (ROOT / "lineups" / f"{pid}.json").write_text(json.dumps(lineup, indent=2, ensure_ascii=False) + "\n")
            key = json.loads(base64.b64decode((ROOT / "keys" / f"{p['repeat_of']}.key").read_text().strip()))
            key["prompt_id"] = pid
            key["repeat_of"] = p["repeat_of"]
            (ROOT / "keys" / f"{pid}.key").write_text(base64.b64encode(json.dumps(key).encode()).decode() + "\n")
            built += 1
            continue

        responses = load_responses(pid)
        if responses is None:
            skipped.append(pid)
            continue

        targets = [r for r in responses if r.get("is_target")]
        if p.get("canary") and targets:
            sys.exit(f"{pid} is the canary but has an is_target response. Fix responses/{pid}.json.")
        if not p.get("canary") and len(targets) != 1:
            sys.exit(f"{pid}: expected exactly one is_target response, found {len(targets)}.")

        assignment = {}
        if targets:
            t_letter = target_letter_for[pid]
            assignment[t_letter] = targets[0]
            foils = [r for r in responses if not r.get("is_target")]
            rng.shuffle(foils)
            rest = [l for l in LETTERS if l != t_letter]
            for letter, foil in zip(rest, foils):
                assignment[letter] = foil
        else:  # canary: everyone is a foil
            shuffled = responses[:]
            rng.shuffle(shuffled)
            for letter, r in zip(LETTERS, shuffled):
                assignment[letter] = r

        lineup = {
            "prompt_id": pid,
            "category": p.get("category", ""),
            "prompt_text": p["text"],
            "options": [{"letter": l, "text": assignment[l]["text"]} for l in LETTERS],
        }
        key = {
            "prompt_id": pid,
            "seed": args.seed,
            "canary": bool(p.get("canary")),
            "target_letter": next((l for l in LETTERS if assignment[l].get("is_target")), None),
            "map": {l: assignment[l]["model"] for l in LETTERS},
        }
        (ROOT / "lineups" / f"{pid}.json").write_text(json.dumps(lineup, indent=2, ensure_ascii=False) + "\n")
        encoded = base64.b64encode(json.dumps(key).encode()).decode()
        (ROOT / "keys" / f"{pid}.key").write_text(encoded + "\n")
        built += 1

    print(f"Built {built} lineup(s) with seed {args.seed}.")
    if skipped:
        print(f"Skipped (no responses yet): {', '.join(skipped)}")
    if real:
        counts = {}
        for pid in target_letter_for:
            if (ROOT / "lineups" / f"{pid}.json").exists():
                counts[target_letter_for[pid]] = counts.get(target_letter_for[pid], 0) + 1
        print(f"Target-letter balance (built trials): { {l: counts.get(l, 0) for l in LETTERS} }")


if __name__ == "__main__":
    main()
