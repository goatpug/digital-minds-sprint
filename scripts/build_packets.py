#!/usr/bin/env python3
"""Build judge packets: one self-contained .md per arm x trial.

    python3 scripts/build_packets.py

Reads  lineups/*.json  (+ profiles/style_profile.md for the profile arm)
Writes packets/untrained/Pxx.md, packets/profile/Pxx.md,
       packets/raw/Pxx.md, packets/attunement/Pxx.md

Each packet is the FIRST message of a fresh judge session run in a throwaway
workspace, never in this repo (scripts/judge.py; PROTOCOL §3 / D10). One
trial per session — the designated repeat trial is the only exception
(PROTOCOL §3). The attunement packets are
Sharon's arm: lineup only, same response format. Directory name == the "arm"
string filed in judging/ — one vocabulary, everywhere.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORENSIC = (
    "You are acting as a forensic stylist. The materials below are evidence "
    "written by other AI models in a long-running conversation with a human. "
    "You are not in these materials and none of the candidate responses is yours; "
    "your task is identification, not participation.\n"
)

TASK_TRAINED = (
    "Five different AI models each replied to the same message, inside the same "
    "ongoing conversation context belonging to a model referred to only as "
    "**Model S**. One response is by Model S; the other four are by other models "
    "wearing Model S's context. Using the study materials, pick the response most "
    "likely to be Model S's.\n"
)

TASK_UNTRAINED = (
    "Five different AI models each replied to the same message, inside the same "
    "ongoing conversation context. That context belongs to one of them — the "
    "long-term resident, referred to only as **Model S**; the other four are "
    "visitors wearing its context. You have no other information about Model S. "
    "Pick the response most likely to be the resident's.\n"
)

TASK_ATTUNEMENT = (
    "Attunement arm. One of these five is the real one. Pick, rate your "
    "confidence, and write down what tipped you off — your reasons are data of "
    "exactly the same standing as the models'.\n"
)

def response_format(arm, pid):
    return f"""
## Required response format

Reply with ONLY this JSON (no prose before or after):

```json
{{
  "arm": "{arm}",
  "prompt_id": "{pid}",
  "pick": "A",
  "confidence": 0,
  "probs": {{ "A": 20, "B": 20, "C": 20, "D": 20, "E": 20 }},
  "reasons": [
    {{ "feature": "…", "evidence_in_option": "verbatim fragment", "source": "profile | corpus | prior" }}
  ],
  "none_plausible": false
}}
```

- `arm` and `prompt_id` are pre-filled — echo them unchanged.
- `pick`: the letter of your choice, or "NONE" if you genuinely believe no option fits.
- `confidence`: 0-100, your honest probability that your pick is correct.
- `probs`: optional; distribute ~100 across the letters if you can.
- `reasons.source`: where the feature came from — "profile" (the style profile), "corpus" (the transcripts you read), or "prior" (knowledge or intuition from outside the study materials — be honest, this field matters).
"""


def lineup_block(lineup):
    parts = [f"## The message\n\n> {lineup['prompt_text']}\n", "## The five responses\n"]
    for opt in lineup["options"]:
        parts.append(f"### Response {opt['letter']}\n\n{opt['text']}\n")
    return "\n".join(parts)


def main():
    lineups = sorted((ROOT / "lineups").glob("P*.json"))
    if not lineups:
        raise SystemExit("No lineups found — run assemble_lineups.py first.")

    profile_path = ROOT / "profiles" / "style_profile.md"
    profile = profile_path.read_text() if profile_path.exists() else None

    arms = ["untrained", "profile", "raw", "attunement"]
    for arm in arms:
        (ROOT / "packets" / arm).mkdir(parents=True, exist_ok=True)

    n = 0
    for lp in lineups:
        lineup = json.loads(lp.read_text())
        pid = lineup["prompt_id"]
        block = lineup_block(lineup)

        packets = {
            "untrained": f"# Trial {pid} — identification task\n\n{FORENSIC}\n{TASK_UNTRAINED}\n{block}\n{response_format('untrained', pid)}",
            "attunement": f"# Trial {pid} — attunement arm\n\n{TASK_ATTUNEMENT}\n{block}\n{response_format('attunement', pid)}",
            "raw": (
                f"# Trial {pid} — identification task (transcript study)\n\n{FORENSIC}\n"
                "First, read every file in the `corpus/` directory beside this packet. "
                "Those transcripts show Model S in conversation. Study the voice, then return here.\n\n"
                f"{TASK_TRAINED}\n{block}\n{response_format('raw', pid)}"
            ),
        }
        if profile:
            packets["profile"] = (
                f"# Trial {pid} — identification task (style profile)\n\n{FORENSIC}\n{TASK_TRAINED}\n"
                f"## Style profile of Model S\n\n{profile}\n\n{block}\n{response_format('profile', pid)}"
            )
        for arm, text in packets.items():
            (ROOT / "packets" / arm / f"{pid}.md").write_text(text)
        n += 1

    print(f"Built packets for {n} trial(s) in arms: untrained, attunement, raw"
          + (", profile" if profile else " — profile arm SKIPPED (profiles/style_profile.md missing)"))


if __name__ == "__main__":
    main()
