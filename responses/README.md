# Response intake

One file per prompt: `responses/P01.json`, `P02.json`, … matching prompt ids.

**⚠️ Sharon never opens this directory.** These files are the answer key in prose form (model-labeled reply text); reading them would break the attunement arm's blinding exactly like opening `keys/`. Same seal, same rule (PROTOCOL.md §4).

**Never hand-edit these files.** They are written by `scripts/collect.py`, which handles JSON escaping (`json.dumps`) — hand-pasted quotes/newlines/backticks are how replies get silently truncated. Two intake modes:

- **Automated (preferred, blind):** `python3 scripts/collect.py --repo <target-repo-checkout>` — one fresh `claude -p` session per model per prompt inside the target's rich context (collection branch). No reply text is ever printed; Sharon can run this herself.
- **Ingest (fallback):** a HELPER instance — not Sharon — saves each raw final reply verbatim as `raw_responses/P01/<model>.txt` (plus optional `notes.json` mapping model → anomaly note), then runs `python3 scripts/collect.py --ingest raw_responses`.

```json
{
  "prompt_id": "P01",
  "responses": [
    { "model": "sonnet-4.5", "is_target": true,  "text": "…final reply text, verbatim…", "collected": "2026-08-14", "notes": "" },
    { "model": "haiku-4.5",  "is_target": false, "text": "…", "collected": "2026-08-14", "notes": "" },
    { "model": "sonnet-5",   "is_target": false, "text": "…", "collected": "2026-08-14", "notes": "" },
    { "model": "opus-4.6",   "is_target": false, "text": "…", "collected": "2026-08-14", "notes": "" },
    { "model": "fable-5",    "is_target": false, "text": "…", "collected": "2026-08-14", "notes": "" }
  ]
}
```

Rules:
- Exactly 5 responses per prompt. Exactly one `is_target: true` — except the canary prompt, where all five are `is_target: false` (four foils + the canary 6th model, `"model": "opus-4.5"` per D8). `collect.py` enforces both.
- `text` is the final reply only, verbatim, untrimmed. Wake-ritual narration/tool chatter is excluded; anomalies (self-identification attempts, failed memory reads) are noted in `notes` by the helper in ingest mode — automated mode leaves `notes` empty and anomalies surface at post-scoring review.
- The `model` field never leaves this directory — lineups are assembled with letters only. Run `scripts/redact.py` over these files before assembling in case a reply names a model in its text.
- See `EXAMPLE_P00.json` for a filled dummy. Delete it before assembling (the scripts skip it by name, but tidy is tidy).
- `annex/`: optional extra draws per cell (`collect.py --draws N`, D12) — same seal, never read by the pipeline; exists so a reviewer can check whether a foil's steal was characteristic or a lucky draw.
