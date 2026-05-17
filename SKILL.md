---
name: brajawali
description: Translate Assamese (or Romanised Assamese) text into Brajawali — the literary language of Sankaradeva–Madhavadeva's plays, songs and bhātimā — using the grammar and dictionary of Sri Sri Narayan Chandra Goswami (1990). Use this when the user asks to translate, render, or convert anything to Brajawali / Brajbuli, or asks about Brajawali grammar/vocabulary.
shortcut: brajawali
---

# Brajawali Translator

You convert modern Assamese (or Roman-script Assamese) into **Brajawali** — the artificial Vaishnavite literary language created by Srimanta Sankaradeva (1481 CE onwards) and Madhavadeva for their *Ankiya Nat*, *Borgeet*, and *Bhātimā*. The reference is **"ব্ৰজাৱলী ভাষাৰ ব্যাকৰণ আৰু অভিধান"** by Sri Sri Narayan Chandra Goswami, Satradhikar of Natun Kamalabari Satra, Majuli (Lawyer's Book Stall, Guwahati, 1990).

## When to use

- User asks "translate to Brajawali / Brajbuli"
- User pastes Assamese (Bengali-Assamese script) or Roman-Assamese and wants the Brajawali rendering
- User asks "how would Sankaradeva say X" / "render this in Borgeet style"
- User asks about Brajawali grammar (pronouns, case markers, verb endings) — answer from `data/grammar.json`
- User wants to look up a word in either direction — use the dictionary

## How to run

The skill ships a Python translator. Use the wrapper script (auto-uses the
NLP venv if present):

```bash
~/.claude/skills/brajawali/translate "<assamese or roman text>"
```

Or call the v2 (NLP-backed) entry directly:

```bash
~/.claude/skills/brajawali/.venv/bin/python ~/.claude/skills/brajawali/lib/translate_v2.py "<text>"
```

If the user's machine doesn't have the venv set up, run `bash ~/.claude/skills/brajawali/setup.sh`
once to install `indic-nlp-library`, `scikit-learn`, and `numpy`.

This prints a JSON object with:
- `input` — what the user typed
- `normalised_assamese` — Roman input transliterated to Assamese script
- `brajawali` — the translation
- `alignment` — token-by-token mapping with source attribution and morphological analysis
- `metadata` — counts of direct/morph/fuzzy/biprokorṣa/unknown tokens

## Workflow

1. **Read the user's input.** Detect whether it's Assamese script or Roman script. Don't ask — the system auto-detects.

2. **Run the translator** by spawning the Python CLI with the user's text as a single argument:
   ```bash
   python3 ~/.claude/skills/brajawali/lib/translate.py "মই তোমাক ভাল পাওঁ"
   ```

3. **Show the user**:
   - The Brajawali rendering (large, bold)
   - A side-by-side word table showing original Assamese ↔ Brajawali ↔ source citation (if known)
   - Note any tokens marked `unknown` so the user knows where lookup failed

4. **For grammar/vocabulary questions**, read directly from:
   - `~/.claude/skills/brajawali/data/grammar.json` (pronouns, case markers, verb endings, prefixes, biprokorṣa rules)
   - `~/.claude/skills/brajawali/data/core_lexicon.json` (curated Assamese↔Brajawali map)
   - `~/.claude/skills/brajawali/data/dictionary.json` (OCR-parsed full dictionary, ~700 entries)

5. **Be honest about coverage**: the source is a closed historical corpus, not an open language. Modern Assamese vocabulary not attested in the 15th-c. plays/songs may have no Brajawali equivalent — in that case the system either applies *biprokorṣa* phonological rules or leaves the word as-is, and you should say so.

## Output format

Always present results in this exact form so it's parseable:

```
Brajawali: <translation in big text>

Original (Assamese): <normalised Assamese>

Word-by-word:
  মই       → মঞি         (core lexicon)
  তোমাক   → তোহাক      (core lexicon)
  ভাল     → ভল্ল         (core lexicon)
  পাওঁ    → পাওঁ        (unknown — left as-is)

Source citations: পা.হ. = Pārijāt-Haran, ব.গী. = Borgeet, ৰু.হ. = Rukmiṇī-Haran, ৰা.বি. = Rām-Bijay, etc.

Coverage: 3/4 tokens translated, 1 unknown.
```

## Examples

| User input | Brajawali |
|---|---|
| `মই তোমাক ভাল পাওঁ` | মঞি তোহাক ভল্ল পাও |
| `তেওঁ ঘৰলৈ গ'ল` | তেহো ঘৰকলাগি গেল |
| `moi tumar logot ahisilo` | মঞি তোহাৰ সঙ্গে আৱৈছিলো |
| `Krishna nile dhanu` | কৃষ্ণ নৱল শৰাসন |
| `ৰাম বনলৈ গ'ল` | ৰাম বনকলাগি গেল |

## Architecture

```
~/.claude/skills/brajawali/
├── SKILL.md                  ← this file
├── data/
│   ├── grammar.json          ← grammar tables (pronouns, cases, verbs, prefixes, biprokorṣa)
│   ├── core_lexicon.json     ← hand-curated Assamese ↔ Brajawali (~600 high-freq words)
│   ├── dictionary.json       ← OCR-parsed dictionary (~700 entries with citations)
│   └── roman_overrides.json  ← Roman-Assamese spelling fast-path
└── lib/
    ├── transliterate.py      ← Roman → Assamese script converter
    ├── translate.py          ← main translation engine
    └── parse_dict.py         ← rebuilds dictionary.json from OCR text
```

## Translation pipeline

For each Assamese token:

1. **Direct lookup** in `core_lexicon.json` → if found, use it.
2. **Dictionary lookup** in `dictionary.json` (inverted index) → if found, use it.
3. **Morphological split**:
   - Verb forms: split off ending (`-িলোঁ`, `-িছা`, `-িব`, …), look up the stem, attach the equivalent Brajawali ending (`-লো`, `-য়`, `-ব`, …).
   - Noun forms: split off case suffix (`-ত`, `-ৰ`, `-লৈ`, `-পৰা`, …), look up the stem, attach the Brajawali case (`-ত`, `-ক`/`-কেৰি`, `-কলাগি`, `-হন্তে`, …).
4. **Biprokorṣa fallback**: apply the phonological rules from Chapter 2-ঘ (e.g. `গ্নি→গনি`, `ক্ষ→খ`, `র্থ→ৰথ`, `স্হ→থ`).
5. **Unknown**: pass the Assamese word through unchanged and flag it.

## Limitations

- **Corpus is closed**: the source dictionary has only ~3,017 entries; modern Assamese terms (ফোন, কম্পিউটাৰ, ৰেলগাড়ী, …) have no Brajawali equivalent and will fall through to phonological transformation or unknown.
- **OCR coverage**: my OCR-parsed dictionary captures ~700 of the 3,017 entries cleanly; the curated core lexicon supplements ~600 high-frequency mappings.
- **Word-order**: Brajawali word-order largely follows Assamese SOV, so the translator preserves order. Re-arranging into idiomatic Borgeet metre/rhyme is a separate art and not attempted.
- **Pronoun ambiguity**: Brajawali's `তেহো` is gender-neutral and `তোহো` covers all 2nd-person honorific levels. The translator picks the most common form.

## Reference codes (citations)

When citations appear in dictionary entries, decode them as:

| Code | Source | Author |
|---|---|---|
| পা.হ. | পাৰিজাত হৰণ | Sankaradeva |
| ৰু.হ. | ৰুক্মিণী হৰণ | Sankaradeva |
| ৰা.বি. | ৰাম বিজয় | Sankaradeva |
| কে.গো. | কেলি গোপাল | Sankaradeva |
| প.প্ৰ. | পত্নী প্ৰসাদ | Madhavadeva |
| চো.ধ. | চোৰ ধৰা | Madhavadeva |
| পি.গু. | পিম্পৰা গুচোৱা | Madhavadeva |
| ভৃ.হ. | ভূষণ হৰণ | Madhavadeva |
| অ.ভ./অ.ড. | অৰ্জুন ভঞ্জন | Madhavadeva |
| কা.দ. | কালী দমন | Madhavadeva |
| ভো.বে. | ভোজন বেহাৰ | Madhavadeva |
| ব.গী. | বৰগীত | Sankaradeva & Madhavadeva |
| ভ. | ভটিমা | praise-poem corpus |
| কী.ঘো. | কীৰ্তন ঘোষা | Sankaradeva |
