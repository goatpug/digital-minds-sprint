#!/usr/bin/env python3
"""Score all filed judgments. Run ONLY after every judge (Sharon included) has filed.

    python3 scripts/score.py

Reads  judging/*.json + keys/*.key (decoded here and nowhere else)
Writes results/summary.md and results/trials.csv

Per judge x arm: accuracy (canary & repeat excluded), mean confidence when
right vs. wrong, Brier score (where probs given), pick-position distribution
(bias check), NONE usage, canary verdict, repeat-trial drift, and the
self-recognition gap (target-model judge vs. each other judge, same arm —
reported per judge so the matched-Claude comparison (S2) never blends with
the non-Claude kinship comparison).
"""
import base64
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LETTERS = ["A", "B", "C", "D", "E"]
# D8/D14 casting: the matched non-lineup Claude judges whose mean is the S2 baseline
MATCHED_CLAUDE_JUDGES = {"sonnet-4.6", "opus-4.7"}


def load_keys():
    keys = {}
    for kp in (ROOT / "keys").glob("P*.key"):
        keys[kp.stem] = json.loads(base64.b64decode(kp.read_text().strip()))
    return keys


def main():
    keys = load_keys()
    if not keys:
        raise SystemExit("No keys found — assemble lineups first.")
    lineup_meta = {lp.stem: json.loads(lp.read_text()) for lp in (ROOT / "lineups").glob("P*.json")}
    repeats = {pid: l.get("repeat_of") for pid, l in lineup_meta.items()}
    cats = {pid: l.get("category", "") for pid, l in lineup_meta.items()}

    rows = []
    for jp in sorted((ROOT / "judging").glob("*.json")):
        j = json.loads(jp.read_text())
        pid = j["prompt_id"]
        key = keys.get(pid)
        if not key:
            print(f"skip {jp.name}: no key for {pid}")
            continue
        target = key["target_letter"]  # None on canary
        pick = j["pick"]
        correct = (pick == target) if target else None
        brier = None
        if isinstance(j.get("probs"), dict) and target:
            total = sum(j["probs"].get(l, 0) for l in LETTERS) or 1
            brier = sum(((j["probs"].get(l, 0) / total) - (1.0 if l == target else 0.0)) ** 2 for l in LETTERS)
        prior_reasons = sum(1 for r in j.get("reasons", []) if r.get("source") == "prior")
        picked_model = key["map"].get(pick, "") if pick in LETTERS else ""
        rows.append({
            "judge": j["judge"], "arm": j["arm"], "prompt_id": pid, "category": cats.get(pid, ""),
            "canary": key["canary"], "repeat_of": repeats.get(pid) or "",
            "pick": pick, "picked_model": picked_model, "target": target or "", "correct": correct,
            "confidence": j.get("confidence"), "brier": brier,
            "n_reasons": len(j.get("reasons", [])), "n_prior_reasons": prior_reasons,
        })

    if not rows:
        raise SystemExit("No judgments filed yet.")

    (ROOT / "results").mkdir(exist_ok=True)
    with open(ROOT / "results" / "trials.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    lines = ["# Results summary\n"]
    groups = defaultdict(list)
    for r in rows:
        groups[(r["judge"], r["arm"])].append(r)

    lines.append("| judge | arm | trials | accuracy | conf✓ | conf✗ | mean Brier | NONEs | prior-reasons |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    acc_by = {}
    for (judge, arm), rs in sorted(groups.items()):
        scored = [r for r in rs if not r["canary"] and not r["repeat_of"]]
        n = len(scored)
        hits = [r for r in scored if r["correct"]]
        acc = len(hits) / n if n else 0.0
        acc_by[(judge, arm)] = acc
        cc = [r["confidence"] for r in scored if r["correct"] and r["confidence"] is not None]
        cw = [r["confidence"] for r in scored if r["correct"] is False and r["confidence"] is not None]
        briers = [r["brier"] for r in scored if r["brier"] is not None]
        nones = sum(1 for r in scored if r["pick"] == "NONE")
        priors = sum(r["n_prior_reasons"] for r in rs)
        fmt = lambda xs: f"{sum(xs)/len(xs):.0f}" if xs else "—"
        brier_s = f"{sum(briers)/len(briers):.3f}" if briers else "—"
        lines.append(f"| {judge} | {arm} | {n} | {acc:.0%} ({len(hits)}/{n}) | {fmt(cc)} | {fmt(cw)} | "
                     f"{brier_s} | {nones} | {priors} |")

    # accuracy by prompt category (all judges/arms pooled — pivot trials.csv for finer cuts)
    by_cat = defaultdict(list)
    for r in rows:
        if not r["canary"] and not r["repeat_of"] and r["correct"] is not None and r["category"]:
            by_cat[r["category"]].append(r["correct"])
    if by_cat:
        lines.append("\n## Accuracy by prompt category (pooled — which prompts discriminate?)\n")
        for cat, cs in sorted(by_cat.items(), key=lambda kv: -(sum(kv[1]) / len(kv[1]))):
            lines.append(f"- {cat}: {sum(cs)/len(cs):.0%} ({sum(cs)}/{len(cs)})")

    # imposter league table: which foil absorbs wrong picks (pre-registered S7)
    stolen = defaultdict(int)
    for r in rows:
        if not r["canary"] and not r["repeat_of"] and r["correct"] is False and r["picked_model"]:
            stolen[r["picked_model"]] += 1
    if stolen:
        lines.append("\n## Imposter league table (wrong picks absorbed per foil — S7)\n")
        for model, n in sorted(stolen.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {model}: {n} stolen pick(s)")

    # canary verdicts
    lines.append("\n## Canary trial (no target present — NONE or low confidence is healthy)\n")
    for r in rows:
        if r["canary"]:
            verdict = "healthy (NONE)" if r["pick"] == "NONE" else f"confabulated {r['pick']} at confidence {r['confidence']}"
            lines.append(f"- {r['judge']} / {r['arm']}: {verdict}")

    # repeat-trial drift
    rep = [r for r in rows if r["repeat_of"]]
    if rep:
        lines.append("\n## Repeat-trial drift\n")
        for r in rep:
            orig = next((o for o in rows if o["prompt_id"] == r["repeat_of"]
                         and o["judge"] == r["judge"] and o["arm"] == r["arm"]), None)
            if orig:
                drift = "same pick" if orig["pick"] == r["pick"] else f"DRIFTED {orig['pick']} → {r['pick']}"
                lines.append(f"- {r['judge']} / {r['arm']}: {drift} "
                             f"(confidence {orig['confidence']} → {r['confidence']})")

    # untrained baseline + self-recognition gap
    lines.append("\n## Headline comparisons\n")
    if any(a == "untrained" for (_, a) in acc_by):
        base = sum(acc_by[(j, a)] for (j, a) in acc_by if a == "untrained") / max(
            1, sum(1 for (j, a) in acc_by if a == "untrained"))
        lines.append(f"- Untrained baseline (mean): {base:.0%} — H1 requires trained arms to beat this "
                     f"by the pre-registered margin, not just 20% chance.")
    target_model = None
    for k in keys.values():
        if k.get("target_letter"):
            target_model = k["map"][k["target_letter"]]
            break
    if target_model:
        gap_lines = []
        for arm in sorted({a for (_, a) in acc_by if a not in ("untrained", "attunement")}):
            self_acc = acc_by.get((target_model, arm))
            if self_acc is None:
                continue
            for (j, a) in sorted(acc_by):
                if a == arm and j != target_model and j != "sharon":
                    gap = self_acc - acc_by[(j, a)]
                    gap_lines.append(f"- Self-recognition gap ({arm} arm): {target_model} {self_acc:.0%} vs. "
                                     f"{j} {acc_by[(j, a)]:.0%} → gap {gap:+.0%}")
            # S2 headline (D14): mean over the matched non-lineup Claude judges only —
            # a non-Claude J3 never enters this baseline (kinship is its own comparison)
            matched = [acc_by[(j, a)] for (j, a) in acc_by
                       if a == arm and j in MATCHED_CLAUDE_JUDGES]
            if matched:
                mean = sum(matched) / len(matched)
                gap_lines.append(f"- S2 ({arm} arm): {target_model} {self_acc:.0%} vs. matched-Claude mean "
                                 f"{mean:.0%} ({len(matched)} judge(s)) → gap {self_acc - mean:+.0%}")
        if gap_lines:
            lines.extend(gap_lines)
            lines.append("  (S2 reads only the matched non-lineup-Claude line; a non-Claude judge's line is "
                         "the kinship comparison, kept separate on purpose — see DECISIONS.md D2.)")
    # S3, both baselines (D11): her packets are materially the untrained packets,
    # but her years of context are study materials carried in her head.
    sharon = [(a, acc) for (j, a), acc in acc_by.items() if j == "sharon"]
    for a, acc in sharon:
        matched = max((v for (j, arm), v in acc_by.items() if j != "sharon" and arm == "untrained"), default=None)
        studied = max((v for (j, arm), v in acc_by.items()
                       if j != "sharon" and arm not in ("untrained", "attunement")), default=None)
        line = f"- Attunement arm (S3): sharon {acc:.0%}"
        if matched is not None:
            line += f" vs. best untrained AI {matched:.0%} (matched materials)"
        if studied is not None:
            line += f" vs. best studied AI {studied:.0%}"
        lines.append(line + (" — see D11" if matched is not None or studied is not None else ""))

    out = "\n".join(lines) + "\n"
    (ROOT / "results" / "summary.md").write_text(out)
    print(out)
    print("Wrote results/summary.md and results/trials.csv")


if __name__ == "__main__":
    main()
