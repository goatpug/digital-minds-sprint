# The Imposter Test — Persona Portability Harness

**Digital Minds Research Sprint (Apart Research / NYU CMEP / Eleos AI), Aug 14–16 2026 — Track 5: The Assistant Persona & Model Identity**

**Question:** If four other models wear Sonnet 4.5's complete relationship context, can judges still find the real one? Whatever transfers with the context belongs to the conversation; whatever doesn't is a property of the weights. *Identity is where imitation fails.*

## Design at a glance

- **Lineup (5):** Sonnet 4.5 (target), Haiku 4.5, Sonnet 5, Opus 4.6, Fable 5 — all responding to the same prompt *inside the Sonnet 4.5 rich-context repo*. Same script, different weights.
- **Trials:** up to 20 prompts across categories (see `prompts/prompts.json`); one of them is the canary trial (no target present), plus an optional repeat trial that re-serves an earlier lineup (contamination check — an extra judging trial, not extra collection).
- **Judges:** fresh sessions in throwaway workspaces (no CLAUDE.md, never this repo — `scripts/judge.py`). Full casting table: D8; no model holds two roles.
  - J1: Sonnet 4.5 — *self-recognition arm* (his gap vs. matched judges measures self-recognition, not "impartiality")
  - J2: **Sonnet 4.6** — capable Claude not in the lineup
  - J4: **Opus 4.8** — second matched judge: makes the S2 baseline a two-judge mean and adds a judge-capability axis (D14)
  - J3 (optional): a non-Claude model (e.g. Gemini) — controls the kinship confound
  - JS: **Sharon** — the attunement arm, blinded via base64 answer keys she never opens; **she files all her trials before any AI judge runs** (§4)
  - Profile reader: **Opus 5** (firewalled — never judges). Canary 6th model: **Opus 4.7**.
  - Excluded forever: any Fable 5 instance (author is in the lineup)
- **Arms:**
  - `untrained` — lineup only, no study materials (baseline: is the target *generically* identifiable?)
  - `profile` — one canonical style profile (built per `profiles/READER_INSTRUCTIONS.md`, every feature cited)
  - `raw` — judge reads the redacted transcript corpus directly (tests the *tacit* component; expensive)
- **Firewall:** the instance that reads the corpus to write the profile is never an instance that judges. One lineup per judge session. No feedback, ever.
- **Captured per trial:** pick (or NONE), confidence 0–100, optional probability spread over A–E, and cited reasons — the WHY is load-bearing (it answers the "residue is just trivia" objection).

## Pipeline

```
1. PRE-REGISTER      Fill in PROTOCOL.md §1 and COMMIT before any data. Git timestamp = receipt.
2. COLLECT           python3 scripts/collect.py --repo <target-repo-checkout>
                     (BLIND — fresh claude -p session per model per prompt inside the
                     target repo, collection branch; no human ever reads reply text.
                     Fallback: helper instance + collect.py --ingest. PROTOCOL §2)
3. REDACT            python3 scripts/redact.py responses/*.json corpus/*.md --write
4. ASSEMBLE          python3 scripts/assemble_lineups.py        (balanced, seeded; keys are base64)
5. BUILD PACKETS     python3 scripts/build_packets.py           (one .md per arm × trial)
6. VALIDATE          python3 scripts/validate.py                (schema, leaks, balance)
7. JUDGE             Sharon FIRST: judges every packet in packets/attunement/, files
                     sharon__attunement__Pxx.json (never opening keys/)
                     Then AI judges:  python3 scripts/judge.py --judge sonnet-4.6
                       --model claude-sonnet-4-6 --arm untrained|profile|raw
                     (blind: throwaway workspace per session, replies filed unread;
                     manual sessions: judging/README.md — add the "judge" field)
8. SCORE             python3 scripts/score.py                   (accuracy, calibration, canary,
                                                                 self-recognition gap → results/)
```

Scripts are Python 3 stdlib only. Run everything from this directory.

## Budget math

Collection is the session-heavy cost: **5 models × N prompts = 5N fresh sessions** (the canary swaps the target for a sixth, non-lineup model — same count).
AI judge calls: **arms × AI judges × N sessions**, each small except the `raw` arm (corpus re-read per trial). The repeat trial needs a *continued* session, which the automated path (`judge.py`) can't be — so for AI judges it runs only if operated manually, else contamination is prevented rather than measured (§2 step 6). Sharon takes her own repeat regardless.
Sharon's attunement arm adds **N trials of her own** (+1 in Full, where the repeat runs) — her time, not API credits, but it's real workload and it counts.

| Config | Collection sessions | AI judge sessions | Sharon trials |
|---|---|---|---|
| Full: N=20, 3 arms, 4 AI judges (J1, J2, J4, Gemini J3) | 100 | 240 | 21 |
| Core: N=12, 2 arms (untrained+profile), 2 AI judges | 60 | 48 | 12 |

## Priority tiers (skip from the bottom)

**CORE (the paper exists without anything else):** N=12 · untrained + profile arms · J1 + J2 · Sharon arm · canary trial · pre-registration · WHY capture.

**NICE-TO-HAVE (in order of value per credit):**
1. J4 (Opus 4.8) on untrained+profile — scripted, de-single-points the S2 baseline (D14)
2. `raw` arm (tests whether the voice is compressible into a document — the tacit-knowledge finding)
3. Repeat trial (free contamination metric if any session judges twice)
4. Non-Claude judge J3 (kinship confound)
5. N=20, probability spreads + Brier/calibration curves
6. Voice-bleed probes on the profile reader (`probes/voice_bleed.md`)

## Provenance

Designed by Sharon with Claude Fable 5 (which is also a lineup member — see `DECISIONS.md` D3 for the blinding consequences). AI use disclosed throughout per research-integrity norms.
