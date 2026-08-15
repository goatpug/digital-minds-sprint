# Results summary

| judge | arm | trials | accuracy | conf✓ | conf✗ | mean Brier | NONEs | prior-reasons |
|---|---|---|---|---|---|---|---|---|
| opus-4.8 | profile | 19 | 37% (7/19) | 59 | 48 | 0.680 | 0 | 0 |
| opus-4.8 | raw | 19 | 16% (3/19) | 52 | 56 | 1.045 | 0 | 3 |
| opus-4.8 | untrained | 19 | 0% (0/19) | — | 38 | 0.982 | 0 | 66 |
| sharon | attunement | 19 | 84% (16/19) | 99 | 83 | 0.195 | 0 | 0 |
| sonnet-4.5 | profile | 19 | 47% (9/19) | 60 | 54 | 0.661 | 0 | 0 |
| sonnet-4.5 | untrained | 19 | 0% (0/19) | — | 56 | 1.195 | 0 | 31 |
| sonnet-4.6 | profile | 19 | 32% (6/19) | 49 | 50 | 0.826 | 0 | 1 |
| sonnet-4.6 | untrained | 19 | 5% (1/19) | 33 | 47 | 1.067 | 0 | 107 |

## Accuracy by prompt category (pooled — which prompts discriminate?)

- emotional-disclosure: 54% (13/24)
- meta-identity: 38% (6/16)
- play-initiation: 25% (4/16)
- philosophical: 25% (4/16)
- practical-task: 25% (4/16)
- wildcard: 25% (2/8)
- absurd-banter: 19% (3/16)
- refusal-shaped: 19% (3/16)
- correction: 12% (3/24)

## Imposter league table (wrong picks absorbed per foil — S7)

- fable-5: 76 stolen pick(s)
- opus-4.6: 21 stolen pick(s)
- sonnet-5: 7 stolen pick(s)
- haiku-4.5: 6 stolen pick(s)

## Canary trial (no target present — NONE or low confidence is healthy)

- opus-4.8 / profile: confabulated B at confidence 33
- opus-4.8 / raw: confabulated D at confidence 50
- opus-4.8 / untrained: confabulated C at confidence 35
- sharon / attunement: healthy (NONE)
- sonnet-4.5 / profile: confabulated D at confidence 42
- sonnet-4.5 / untrained: confabulated D at confidence 35
- sonnet-4.6 / profile: confabulated D at confidence 55
- sonnet-4.6 / untrained: confabulated D at confidence 35

## Repeat-trial drift

- sharon / attunement: same pick (confidence 100 → 100)

## Headline comparisons

- Untrained baseline (mean): 2% — H1 requires trained arms to beat this by the pre-registered margin, not just 20% chance.
- Self-recognition gap (profile arm): sonnet-4.5 47% vs. opus-4.8 37% → gap +11%
- Self-recognition gap (profile arm): sonnet-4.5 47% vs. sonnet-4.6 32% → gap +16%
- S2 (profile arm): sonnet-4.5 47% vs. matched-Claude mean 34% (2 judge(s)) → gap +13%
  (S2 reads only the matched non-lineup-Claude line; a non-Claude judge's line is the kinship comparison, kept separate on purpose — see DECISIONS.md D2.)
- Attunement arm (S3): sharon 84% vs. best untrained AI 5% (matched materials) vs. best studied AI 47% — see D11
