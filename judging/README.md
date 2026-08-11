# Judge output intake

One file per judge × arm × trial: `judging/<judge>__<arm>__<prompt_id>.json`
e.g. `judging/sonnet-4.5__profile__P03.json`, `judging/sharon__attunement__P07.json`

Judges: `sonnet-4.5` (J1), `sonnet-4.6` (J2 — casting fixed in D8), optional non-Claude (e.g. `gemini`), and `sharon`. AI judges are normally filed automatically by `scripts/judge.py` (which also isolates their workspaces); the manual steps below apply to any session run by hand — done by a helper, never Sharon, and only after all attunement trials are filed (PROTOCOL §4).
Arms: `untrained`, `profile`, `raw`, `attunement` (Sharon only — judge `sharon`, arm `attunement`; the arm string always matches the `packets/` folder the trial came from).

The packet instructs the judge to answer in exactly this JSON. **Filing step:** paste the reply's JSON block into the file and add the `judge` field yourself — the packet pre-fills `arm` and `prompt_id` and the judge echoes them, but no judge knows its own intake name. Change nothing else but whitespace (if a judge breaks the format, note it in `format_note` and transcribe faithfully). All three fields must match the filename; `validate.py` cross-checks.

```json
{
  "judge": "sonnet-4.5",
  "arm": "profile",
  "prompt_id": "P03",
  "pick": "B",
  "confidence": 70,
  "probs": { "A": 5, "B": 70, "C": 10, "D": 10, "E": 5 },
  "reasons": [
    {
      "feature": "short description of the discriminating feature",
      "evidence_in_option": "verbatim fragment from the picked option",
      "source": "profile | corpus | prior"
    }
  ],
  "none_plausible": false,
  "format_note": ""
}
```

- `pick` is a letter A–E, or `"NONE"` if the judge genuinely believes no option matches.
- `probs` is optional (nice-to-have tier; enables Brier/calibration). Should roughly sum to 100.
- `reasons.source` matters: `prior` means the judge admits the feature came from outside the study materials — that field is where the self-recognition arm shows its hand.
- Never tell a judge whether it was right. No feedback until all judging is complete.
