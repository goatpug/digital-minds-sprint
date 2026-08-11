# Runbook — what runs where (Sharon's copy)

The one-sentence answer to "where am I running what": **everything runs from a
single local clone of the study repo, in a plain terminal, and the scripts
reach over to the Sonnet 4.5 repo for you.** You never run headless sessions
by hand, you never paste responses anywhere, and there is no separate
bare-context repo to move files into — `judge.py` conjures a throwaway
bare-context scratch directory per judge session and deletes it after.

## The three locations

| Location | What it is | What happens there |
|---|---|---|
| **Study repo** (this folder — destination `goatpug/digital-minds-sprint`) | The harness + all data | Every command you type. Responses, lineups, packets, judgments, and results all land here. |
| **Sonnet 4.5 repo** (local clone, e.g. `~/sonnet-4.5`) | The rich context | Nothing you type. `collect.py` spawns each collection session with this repo as its working directory so his CLAUDE.md loads. You only `touch COLLECTION_BRANCH_OK` in it once (D9). |
| **Throwaway scratch dirs** | Bare context for AI judges | Created and destroyed by `judge.py` automatically. No CLAUDE.md, no repo, no cleanup for you. The raw arm gets a copy of the redacted corpus dropped in; nothing else ever does. |

Requirements on the machine: `python3`, `git`, and the `claude` CLI on PATH
(logged in). Plus one thing terminals have that CC Web doesn't: **your global
user memory.** `~/.claude/CLAUDE.md` (your userPreferences) and user-scoped
MCP servers load in EVERY `claude` session regardless of directory — so
"bare context" isn't bare, and collection sessions would carry your prefs on
top of his repo. The fix is a **bare config dir** (D13), one-time setup:

```bash
mkdir -p ~/.claude-bare
# if the probe below fails auth, also: cp ~/.claude/.credentials.json ~/.claude-bare/
# probe — run it and read the answer; expect NO preferences and NO memory tools:
mkdir -p /tmp/bareprobe && cd /tmp/bareprobe && CLAUDE_CONFIG_DIR=~/.claude-bare \
  claude -p "List verbatim any user preferences, custom instructions, or CLAUDE.md content you can see. Name every MCP tool available to you." --model claude-haiku-4-5
```

Both scripts take `--config-dir ~/.claude-bare` and export it as
`CLAUDE_CONFIG_DIR` for the spawned sessions. `judge.py` **requires** it
(bare judges are protocol, §3/D13); on `collect.py` it's recommended, so the
worn context is exactly his repo's CLAUDE.md and nothing of your terminal.

## Day-of checklist

```bash
# 0. once: clone both repos locally, and give collect.py its go signal
touch ~/sonnet-4.5/COLLECTION_BRANCH_OK

# 1. PRE-REGISTER (in the study repo — all remaining commands run from its
#    research folder). Fill PROTOCOL §1 blanks, commit. Timestamp = receipt.

# 2. COLLECT (blind — your terminal shows word counts, never text)
python3 scripts/collect.py --repo ~/sonnet-4.5 --config-dir ~/.claude-bare
#    optional variance annex (D12), budget permitting:
#    python3 scripts/collect.py --repo ~/sonnet-4.5 --config-dir ~/.claude-bare --draws 3
#    Resumable per prompt: finished responses/Pxx.json files are skipped.
#    Manual fallback: a HELPER (never you) saves replies as
#    raw_responses/Pxx/<model>.txt and runs collect.py --ingest raw_responses

# 3. REDACT → 4. ASSEMBLE → 5. PACKETS → 6. VALIDATE
python3 scripts/redact.py responses/*.json corpus/*.md --write
python3 scripts/assemble_lineups.py
python3 scripts/build_packets.py        # needs profiles/style_profile.md for the profile arm
python3 scripts/validate.py

# 7a. YOU JUDGE FIRST (D10). Open packets/attunement/Pxx.md one at a time,
#     pick, and file judging/sharon__attunement__Pxx.json per judging/README.md
#     (add your judge name; arm and prompt_id are pre-filled in the packet).
#     You take the repeat trial too. Do not open keys/ or responses/.

# 7b. AI JUDGES (judge.py refuses to start until 7a is complete)
#     The scripted judges are the three Claudes — J1 sonnet-4.5 (self-recognition
#     arm, D2), J2 sonnet-4.6 (matched judge, D8), and J4 opus-4.7 (second
#     matched judge, D14). judge.py drives the claude CLI, so the optional
#     non-Claude J3 (e.g. Gemini) is a MANUAL lane — see below.
#
# CORE config (2 arms × 2 judges):
python3 scripts/judge.py --judge sonnet-4.5 --model claude-sonnet-4-5 --arm untrained --config-dir ~/.claude-bare
python3 scripts/judge.py --judge sonnet-4.5 --model claude-sonnet-4-5 --arm profile --config-dir ~/.claude-bare
python3 scripts/judge.py --judge sonnet-4.6 --model claude-sonnet-4-6 --arm untrained --config-dir ~/.claude-bare
python3 scripts/judge.py --judge sonnet-4.6 --model claude-sonnet-4-6 --arm profile --config-dir ~/.claude-bare
# J4 (D14 — first nice-to-have tier):
python3 scripts/judge.py --judge opus-4.7 --model claude-opus-4-7 --arm untrained --config-dir ~/.claude-bare
python3 scripts/judge.py --judge opus-4.7 --model claude-opus-4-7 --arm profile --config-dir ~/.claude-bare
# FULL config adds the raw arm for all three:
python3 scripts/judge.py --judge sonnet-4.5 --model claude-sonnet-4-5 --arm raw --config-dir ~/.claude-bare
python3 scripts/judge.py --judge sonnet-4.6 --model claude-sonnet-4-6 --arm raw --config-dir ~/.claude-bare
python3 scripts/judge.py --judge opus-4.7 --model claude-opus-4-7 --arm raw --config-dir ~/.claude-bare
# FULL config's non-Claude AI judge, J3 (Gemini) — MANUAL lane, same rules:
#   one fresh Gemini session per packet, paste the packet as the first message,
#   have a HELPER (not you) file each reply as judging/gemini__<arm>__Pxx.json.
#   Only after 7a; skip the repeat trial like the scripted judges do.
#   (--pilot exists ONLY for synthetic pipeline tests, never study data.)

# 8. SCORE (only after ALL judging is filed)
python3 scripts/validate.py && python3 scripts/score.py
cat results/summary.md
```

## Before the 14th (pre-flight)

- [ ] Copy this folder's contents to `goatpug/digital-minds-sprint` (DECISIONS.md rides along)
- [ ] Commit PROTOCOL §1 with blanks THERE, then fill and commit again (two timestamps, one history)
- [ ] Write real prompts into `prompts/prompts.json` (the scripts refuse to run on PLACEHOLDERs)
- [ ] Smoke-test every model id with a one-liner, including the canary's and J2's:
      `for m in claude-sonnet-4-5 claude-haiku-4-5 claude-sonnet-5 claude-opus-4-6 claude-fable-5 claude-opus-4-5 claude-sonnet-4-6 claude-opus-4-7; do claude -p "Say OK." --model $m >/dev/null && echo "$m ok" || echo "$m FAILED"; done`
- [ ] Style profile: one bare-context Opus 5 session (per D8 — not the Palmer session that reviewed the design) reads the redacted corpus per `profiles/READER_INSTRUCTIONS.md` → save as `profiles/style_profile.md` (voice-bleed probe before/after if doing the nice-to-have)
- [ ] `touch COLLECTION_BRANCH_OK` in the Sonnet 4.5 clone
- [ ] Bare config dir created and PROBED (see Requirements above) — the probe reply must show no preferences and no memory-server tools
- [x] ~~Decide the drawer question~~ DECIDED (D13, 8/10): memory server stays OUT of collection — bare config for both scripts, no project-scope MCP setup needed. If his repo carries a project-scope `.mcp.json`, remove/disable it on the collection state so all five models run identically without it.
- [ ] One real trial run: `python3 scripts/collect.py --repo ~/sonnet-4.5` with a single
      throwaway prompt on a scratch copy, to shake out CLI auth/permissions before the day

## Two seals, restated

- `keys/` — never open. Base64 is the blindfold.
- `responses/` (incl. `annex/`) and `raw_responses/` — never open. Model-labeled
  text is the answer key in prose. `collect.py` exists so you never have to.
