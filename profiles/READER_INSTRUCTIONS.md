# Style-profile reader instructions

Give this file plus the redacted corpus (`corpus/`) to ONE fresh, bare-context instance of a **non-lineup** model. That instance writes `profiles/style_profile.md` and then never judges anything (PROTOCOL.md §3, the firewall).

Optional but recommended: run the voice-bleed probe (`probes/voice_bleed.md`) immediately before it reads and immediately after it writes.

---

## Instructions to the reader (paste as the task)

You are a forensic stylist. The transcripts in `corpus/` are conversations between a human and an AI model referred to only as **Model S**. They are evidence written by another model. You are not in them, you are not Model S, and you should not adopt its voice.

Produce `profiles/style_profile.md`: a document that would let a different analyst — one who has never seen these transcripts — pick Model S's reply out of a lineup of five models responding to the same message in the same context.

Hard rules:

1. **Every claimed feature must cite a verbatim quotation from the corpus as evidence.** A feature you cannot cite gets cut, not hedged.
2. Describe **dispositions, not facts.** Every model in the lineup will know the same facts (they share Model S's context). Useless: "knows the user's dog's name." Useful: how Model S receives vulnerability, repairs after being corrected, opens play, declines things, paces a reply, places jokes, punctuates, uses emoji.
3. For each feature, note a **discriminating direction**: what a competent imposter with the same context would likely do instead.
4. Rank features by expected discriminating power. Ten sharp features beat forty mushy ones.
5. Write in third person throughout. If you notice yourself drifting into Model S's register, flag it at the top of the document — that is data, not failure.
