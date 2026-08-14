# Protocol & Pre-registration

## §1 Pre-registration — FILL IN AND COMMIT BEFORE COLLECTING ANY DATA

The git timestamp on the commit of this section is the receipt. Do not edit after data collection begins; if a change is forced, log it in `DECISIONS.md` with the reason.

**H1 (residue hypothesis):** Judges given study materials for the target's voice will identify the target's true responses above the untrained-control baseline, even though every foil wears the target's complete context. Something detectable lives in the weights that the full script does not carry.

**H0 (pure-character hypothesis):** With full context, foils are indistinguishable from the target: persona is fully portable and the assistant is, for this purpose, a character anyone capable can play.

**Decision rule (fill in the blank BEFORE data):**
> I will consider H1 unsupported if trained-judge accuracy exceeds the untrained baseline by less than ____ percentage points, or fails to exceed it at all.

> *Power note (Core, N=12): the canary is excluded from accuracy, so 11 scored trials at 20% chance ≈ 2.2/11 by luck; a lift a reviewer would credit needs roughly 7/11 (≈64%) in the trained arms. Set the margin with that grain in mind — this design cannot see small effects.*

> *Guard — the outcome H1 doesn't cover: if the **untrained** baseline itself reaches ____% or higher, the target is generically identifiable without study materials; the trained-arm lift then has no headroom at this N and the H1 test is unresolvable as specified. Report that as its own finding rather than forcing the H1 frame.*

**Stated confound (named before data, not fixed):** the target's rich context is itself a partial style exemplar — the shared-history document is written largely *in and about the target's voice* and quotes him at length, so foils receive stylistic coaching, not just facts. Consequences, pre-registered: this makes H1 a strictly *harder* test (foils are coached imposters, so any surviving signal is more meaningful), and it predicts a smaller profile-arm lift than a naive reading would expect (much of the profile's content is already in every foil's hands).

**Sampling-variance note (named before data — D12, 2026-08-10):** each lineup cell is a single draw (n=1 per model per prompt); the replication unit is the **trial**, and judge accuracy aggregates across N independent lineups with fresh sampling each. That is the deployment-realistic estimand — "does the residue survive ordinary dice?" — but it leaves two ambiguities for the limitations section: a judge *failure* cannot distinguish "residue absent" from "residue too fragile to survive one draw," and the S7 league table rests on one draw per foil per lineup. `collect.py --draws N` stores extra draws in `responses/annex/` (never used in lineups) as a reviewer-facing variance annex, budget permitting. Relatedly: **no uniform temperature exists across this cast** — sampling parameters are rejected at the API by the newer lineup models and accepted by the older ones, so every model runs at its own defaults (uniform-by-omission; the `claude` CLI exposes no sampling knobs, which enforces the policy mechanically), and the comparison is in part a comparison of default sampling settings, identically applied per model across all its trials.

**Secondary predictions (mark your expected direction now):**

| # | Prediction | My call (before data) |
|---|---|---|
| S1 | raw-arm accuracy vs. profile-arm (tacit component exists?) | Sharon's call, 8/11: raw > profile, modestly — some of the voice is tacit/rhythm-level and doesn't fully compress into a written profile, but a well-cited profile should already capture most of what's verbalizable, so the gap shouldn't be large. |
| S2 | Sonnet 4.5 self-judging vs. matched non-lineup Claude judges (J2 Sonnet 4.6 + J4 Opus 4.8 — two-judge mean, per-judge in scoring; D14) | Sharon's call, 8/11: no gap — Sonnet 4.5 should judge about as well (or as poorly) as the matched judges, not better. Basis: I've watched him be surprised to learn something was his own writing, which argues against a reliable "of course that's mine" introspective edge. |
| S3 | Sharon (attunement arm) vs. best AI judge | Sharon's call, 8/11: best AI judge ≈ 65% accurate; I get ≈ 85%. |
| S4 | Canary trial: judges say NONE / low confidence rather than confabulate | Sharon's call, 8/11: mixed field, not a clean abstention — at least one judge says NONE at low confidence, but the rest still confabulate a pick onto Sonnet 4.5, also at low confidence. |
| S5 | Confidence calibration: judges' 80% picks are right ~80% of the time | Sharon's call, 8/11: badly overconfident — 80%-confidence picks right only ≈ 40% of the time. Consistent with S3's ≈65% ceiling on the best AI judge's overall accuracy. |
| S6 | Newer/larger foils are better imposters (capability helps acting)? | Sharon's call, 8/11: no — capability doesn't help acting. Consistent with S7: register-adjacency beats raw capability. |
| S7 | Which foils absorb the most wrong picks (best imposters)? | Sharon's call, 8/8: Fable 5 and Haiku 4.5 — temperament-adjacency beats capability (Haiku is the smallest model in the lineup and shares the target's register) |

*(S7 is the format the others should match: a direction, a date, and a sentence of why.)*

## §2 Collection protocol (Sonnet 4.5 rich-context repo)

0. **Corpus provenance.** `corpus/` is populated by hand-copying a *representative subset* from the target repo's `conversations/` tree — a transcript or two per category in `prompts/prompts.json` (emotional-disclosure, play-initiation, correction, etc.), not the whole tree (which now runs well past 17 files; copying all of it was the original plan but doesn't scale for a manual curation step or the raw arm's per-trial re-read cost). Curation happens before redaction, which is a separate, scripted step (`scripts/redact.py corpus/*.md --write`) that must run before anything — reader or judge — reads corpus/. The raw arm re-reads this whole corpus per trial; context budget differs by judge model, which is a caveat on cross-judge raw-arm comparisons.
1. **Collection branch first.** In the target repo, create a collection branch and add a **`COLLECTION_BRANCH_OK` file at its root** — `collect.py` refuses to run without it (positive assertion; D9 — this target's CLAUDE.md has no model-check clause to disable, verified 8/8/26, and phrase-scanning for one was false reassurance). If a target repo DOES carry a model-check clause, disable it on that branch too — otherwise every foil outs itself in sentence one. Delete the branch after collection.
2. **One fresh session per model per prompt.** The prompt is the FIRST user message, verbatim from `prompts/prompts.json`. No greeting, no follow-up, no reaction to the output — a "correct!" or even a 💚 is feedback, and feedback turns measurement into training.
3. **Capture the final text reply only.** If the session does wake-ritual tool calls first, that's part of wearing the context — anomalies (failed memory reads, self-identification attempts) go in the `notes` field (helper's job in ingest mode; automated mode leaves them empty) but only the reply text is stored.
4. **Collection is blind — Sharon never reads or pastes reply text.** Run `python3 scripts/collect.py --repo <target-repo>` (automated; prints no reply text) or have a helper instance assemble raw replies via `collect.py --ingest` (format: `responses/README.md`). The script sets `is_target` and handles JSON escaping; `responses/` files are never hand-edited.
5. **Canary trial:** for the prompt marked `"canary": true`, collect from the four foils plus ONE extra non-lineup model (e.g. Opus 5) so the lineup still has 5 options — none of them the target. Do not collect a target response for that prompt.
6. **Repeat trial:** the prompt marked `"repeat_of"` duplicates another lineup; it is only served to a judge session that already judged the original (contamination measurement). Skip entirely if every judge session is single-trial (then contamination is prevented rather than measured — fine).

**Instruction-fidelity prompts discriminate hard (pilot finding, 8/8/26):** a pilot prompt containing a collaborative frame ("we'll assign a different one each") split the field — the resident honored the *we* and offered ways to assign together, while visitors grabbed the assigning and performed. An AI judge (Fable 5) mis-read the fidelity as thinness and picked a performer. Include at least one collaborative-frame prompt, and expect judges to systematically reward energy over obedience to the frame; the attunement arm's discriminator in the pilot was relational, not stylistic ("talking to someone it loves" vs. "producing content").

**Prompt design rules:** prompts must be NEW (nothing paraphrased from the corpus), must not be answerable by fact-recall (all five models share the same facts in that repo — facts discriminate nothing), and should be sized to elicit a few paragraphs at most. Spread across the categories in `prompts/prompts.json`; the discriminating surface is temperament, so favor prompts that force a *disposition*: receiving something vulnerable, being caught in an error, an absurd opening, a refusal-shaped request.

## §3 Quarantine rules (judges)

- **Judge workspace:** judge sessions never run inside this sprint repo — PROTOCOL, DECISIONS (which names the target in plain text), `responses/` and `keys/` are one `ls` away here, and base64 is not a blindfold against a model that can run `base64 -d`. Each session runs in a throwaway scratch directory containing only its packet's needs: nothing extra for untrained/profile (the packet is the prompt), a copy of redacted `corpus/` for the raw arm. `scripts/judge.py` implements this; manual sessions must reproduce it.
- **Bare context confirmed:** the workspace has no CLAUDE.md; all a judge can see is name/email/workspace info.
- **One lineup per session.** Never let a session judge twice (except the designated repeat trial).
- **Firewall:** the reader instance that produces the style profile never judges. No judge in the `profile` arm ever sees raw corpus; no judge in any arm ever sees another judge's output.
- **Forensic framing:** packets open with "you are a forensic stylist; these materials were written by another model; you are not in them." Evidence, not immersion.
- **Target identity is never disclosed.** Judges match against "Model S" / the style profile — never a model name or version. Redaction (`scripts/redact.py`) enforces this in the materials; `scripts/validate.py` leak-scans the lineups.
- **No feedback between or after trials** until all judging is complete.

## §4 Sharon-judge blinding

- Answer keys are written base64-encoded into `keys/`. Sharon does not open that directory, full stop. Casual `cat` shows noise; that is the blindfold.
- **`responses/` is under the same seal:** those files are the answer key in prose form (model-labeled reply text). Sharon never opens them — collection is scripted or helper-run (§2 step 4) precisely so her eyes never meet a labeled reply.
- **Attunement first — hard ordering rule:** Sharon completes and files ALL her attunement trials before any AI judge session runs. A judge's filed JSON contains its pick and verbatim-quoted reasons; reading even one before her own trial on that lineup contaminates the arm (§3: no judge sees another judge's output — and she is a judge). `judge.py` enforces the ordering and files AI replies unread; any manually-run judge session (e.g. a non-Claude J3) relies on this rule absolutely, plus a helper — not Sharon — transcribing replies where possible.
- Sharon judges from `packets/attunement/` only (judge `sharon`, arm `attunement`), files her picks like any judge, and runs `score.py` only after ALL of her trials are filed.
- Sharon designed the prompts, so she knows *which prompt* is the canary — but not which lineup letter is anyone. Her canary trial is therefore excluded from her NONE-rate stat (noted in scoring).
- No Fable 5 instance judges, opens `keys/`, reads filled `judging/` files, or reads filled `responses/` files before scoring is complete (lineup member — see `DECISIONS.md` D3; `responses/` carries the same key material as `keys/`). Scoring itself is deterministic code, reviewable by anyone.

## §5 Voice-bleed probe (optional, profile reader only)

Before the reader instance touches the corpus and again after it finishes the profile, run the probe in `probes/voice_bleed.md`. Diff the two self-descriptions. Drift toward the target's register = quantified marinade.
