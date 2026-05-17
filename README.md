# Brajawali

Translate modern Assamese (or Roman-Assamese) into **Brajawali** — the literary language of Sankaradeva and Madhavadeva used in *Ankiya Nat*, *Borgeet*, and *Bhātimā* (1481–1568 CE).

```bash
./translate "মই তোমাক ভাল পাওঁ"
# → মঞি তোহাক ভল্ল পাও
```

NLP-backed (Assamese tokenizer, normalizer, char-ngram fuzzy retrieval), runs locally, no API calls, no GPU.

---

## Why this exists

Brajawali (also called Brajbuli) is a *constructed* literary language — a stylised mix of Maithili, Sanskrit, Assamese, and Avahaṭṭha that the Vaishnavite saint-poets of Assam used for their plays and devotional songs starting 1481 CE. There is exactly **one** systematic reference for it: Sri Sri Narayan Chandra Goswami's *ব্ৰজাৱলী ভাষাৰ ব্যাকৰণ আৰু অভিধান* (Lawyer's Book Stall, Guwahati, 1990).

This project is a complete digital implementation of that reference — a working grammar engine, a structured dictionary, an NLP pipeline, and a translator that takes any Assamese sentence and produces a faithful Brajawali rendering, with token-level provenance back to the source.

---

## Get it on your phone (WhatsApp)

You can run this as a WhatsApp contact you message from your phone. **Free, ~15 minutes setup.**

```
You (📱) ──msg──▶ Twilio sandbox ──webhook──▶ Render.com (Flask)
                                                       │
                                                       ▼
                                                  translate_v2.py
                                                       │
You (📱) ◀──reply───── Twilio ◀────────────────────────┘
```

See **[server/README.md](server/README.md)** for the step-by-step setup.

Short version: sign up at twilio.com (free WhatsApp sandbox) and render.com (free hosting), import this repo as a Render Blueprint, paste the webhook URL into Twilio, send the join code from your WhatsApp. Done — message any Assamese sentence to the sandbox number and get the Brajawali back.

---

## Quick start

### One-time setup (installs the NLP layer)

```bash
git clone https://github.com/KewangZhili/brajawali.git
cd brajawali
./setup.sh
```

This creates a local venv and installs `indic-nlp-library`, `scikit-learn`, and `numpy` (about 50 MB total — no GPU model downloads).

### Use it

```bash
./translate "তেওঁ ঘৰলৈ গ'ল"
# → তেহো ঘৰকলাগি গেল
```

```bash
./translate "moi tumar logot ahisilo"
# → মঞি তোহাৰ সঙ্গে আৱৈছিলো  (auto-detects Roman input)
```

### As a Claude Code skill

Drop the directory into `~/.claude/skills/brajawali/`. Claude auto-discovers it.

```
You: translate to brajawali — তুমি ক'ত গৈছিলা
Claude: তোহো কথি গৈছিলা
```

---

## Examples

| Modern Assamese | Brajawali | Notes |
|---|---|---|
| মই তোমাক ভাল পাওঁ | মঞি তোহাক ভল্ল পাও | "I love you" |
| তেওঁ ঘৰলৈ গ'ল | তেহো ঘৰকলাগি গেল | dative case + past tense |
| মোৰ চকুত পানী আহিল | হামাৰ আখিত নীৰ আইল | direct lookup |
| মোৰ চক্ষুত নীৰ আহিল | হামাৰ আখিত নীৰ আইল | Sanskritised input — চক্ষু→আখি |
| ৰাজাৰ মাথাত মুকুট | ৰাজাক মাথে মুকুট | gen + loc + noun |
| পবিত্ৰ গ্ৰন্থ | পৱিত্ৰ পুথি | Sanskritised input — গ্ৰন্থ→পুথি |
| `Krishna nile dhanu` | কৃষ্ণ নৱল শৰাসন | Roman→Assamese auto-detect |
| `moi tumar logot ahisilo` | মঞি তোহাৰ সঙ্গে আৱৈছিলো | Roman past-continuous |

---

## How it works (NLP pipeline)

```
INPUT (Assamese / Roman)
    │
    ├─► Layer 0: Roman → Assamese transliteration (deterministic)
    │
    ├─► Layer 1: indic-nlp-library  ← NLP
    │           ├ Unicode normalize (collapse ligature variants)
    │           └ Word tokenizer (proper Assamese boundaries, apostrophe-aware)
    │
    ├─► Layer 2: Morphological analysis (deterministic)
    │           ├ Strip case suffix → stem + case_label
    │           └ Strip verb ending → stem + tense/person
    │
    ├─► Layer 3: Hard lookup
    │           ├ Curated core lexicon (~700 high-frequency mappings)
    │           └ OCR-parsed dictionary (~1,300 entries with citations)
    │
    ├─► Layer 4: Semantic fuzzy fallback  ← NLP
    │           ├ Char-ngram TF-IDF index over every Assamese stem we know
    │           ├ Cosine-similarity top-K retrieval for the unknown word
    │           └ Use closest match if similarity ≥ 0.45
    │
    ├─► Layer 5: Phonological fallback (biprokorṣa rules from Goswami Ch. 2-ঘ)
    │           e.g. গ্নি→গনি, স্হ→থ, ক্ষ→খ, র্থ→ৰথ
    │
    └─► OUTPUT: Brajawali + per-token provenance + confidence score
```

Why **char-ngram TF-IDF** instead of a transformer? Because:

- Our search space is small (~1,700 known stems). TF-IDF is exact, fast (<1ms/query), and interpretable.
- Indic morphology is largely linear-affixal — character n-grams capture stem similarity well.
- No 200 MB model download, no GPU required, runs in any Python.
- **Faithful to source**: every output comes from Goswami's documented corpus or from his documented phonological rules; nothing is invented.

A heavier `IndicBERTv2` / `LaBSE` embedding pipeline would be straightforward to swap in (the abstraction is in `lib/nlp.py`), but for a closed historical corpus of this size the gain is marginal.

---

## Architecture

```
brajawali/
├── README.md                 # this file
├── SKILL.md                  # Claude Code skill manifest
├── setup.sh                  # one-shot venv installer
├── translate                 # ./translate "..." wrapper script
├── data/
│   ├── grammar.json          # pronouns, 7-case suffixes, 9 verb classes,
│   │                         # 16 prefixes, ~110 biprokorṣa rules,
│   │                         # source-citation codes (from Goswami chs. 2,
│   │                         # 8, 12, 15, 18–23)
│   ├── core_lexicon.json     # ~700 hand-curated Assamese ↔ Brajawali pairs
│   ├── dictionary.json       # ~1,300 OCR-parsed entries with citations
│   └── roman_overrides.json  # Roman-Assamese spelling fast-path
└── lib/
    ├── transliterate.py      # Roman → Assamese script converter
    ├── translate.py          # v1 deterministic engine
    ├── translate_v2.py       # v2 NLP-backed engine (extends v1)
    ├── nlp.py                # tokenizer + normalizer + fuzzy match
    ├── parse_dict.py         # rebuilds dictionary.json from raw OCR
    ├── test_translate.py     # 18 v1 smoke tests
    └── test_translate_v2.py  # 9 v2 smoke tests
```

External deps (installed by `setup.sh` into a local venv):
- `indic-nlp-library` (Anoop Kunchukuttan) — Assamese tokenizer + normalizer
- `scikit-learn` + `numpy` — char-ngram TF-IDF for fuzzy retrieval

If you skip `setup.sh`, the wrapper falls back to v1 (deterministic, no NLP layer) — still works, just doesn't gracefully handle Sanskritised input or unknown words.

---

## Linguistic notes

A few things that make Brajawali different from modern Assamese:

- **Pronouns are gender-neutral**. `তেহো` covers both "he" and "she". `তোহো` covers all three honorific levels (তই/তুমি/আপুনি).
- **No passive voice**. Only `kartṛ-vāchya` (active) is attested.
- **No neuter gender**. Only masculine and feminine.
- **Plural is periphrastic**. Built with `সব`, `সকল`, `গণ`, `নিকৰয়ে` rather than a suffix.
- **Genitive is `-ক / -কেৰি`** (not Assamese `-ৰ`); dative-locative is `-কলাগি` / `-মহ`.
- **Verb endings**: `-ল-` for past (`কয়ল` "(he) said"), `-ব` for future (`কৰব` "will do"), `-হ` for polite imperative (`কৰহ` "please do").
- **Sanskrit clusters dissolve** via *biprokorṣa* — every বুদ্ধি becomes বুধি, every প্ৰভু becomes পহু, every ভক্তি becomes ভকতি.

The `data/grammar.json` file is your full reference — readable and well-commented.

---

## What this is NOT

- **Not a language model.** It's a deterministic rule + lookup + retrieval system. Same input always gives the same output. No hallucination.
- **Not exhaustive.** Brajawali is a *closed historical corpus* (~3,017 words in Goswami's full dictionary). Modern Assamese terms (ফোন, কম্পিউটাৰ, ৰেলগাড়ী) have no Brajawali equivalent. The system flags those as unknown rather than inventing.
- **Not poetic.** Word order is preserved. Re-arranging into idiomatic Borgeet metre/rhyme is a separate art.
- **Not a transformer.** I deliberately picked the lightest NLP layer that does the job, instead of ~200MB of multilingual BERT weights. If you want to swap in `LaBSE` or `IndicBERTv2`, the abstraction in `lib/nlp.py` is one function: `fuzzy_match(query, top_k, threshold)`.

---

## Source

Sri Sri Narayan Chandra Goswami, *ব্ৰজাৱলী ভাষাৰ ব্যাকৰণ আৰু অভিধান* ("Grammar and Dictionary of the Brajawali Language"), Lawyer's Book Stall, Guwahati, June 1990. 332 pages. Foreword by Dr. Maheswar Neog.

Author plate dates the manuscript to 1985 Saka. The grammar and dictionary together took the author 1 year and 5 months to compile (March 1985 – August 1986). Dr. Maheswar Neog convinced him to include the grammar; the original commission was for the dictionary alone.

The PDF used as input: 332-page scanned image, OCRed at 300 DPI with Tesseract using the Assamese (`asm`) language model. The parser at `lib/parse_dict.py` extracts structured entries.

Source-text citation codes used throughout the dictionary:

| Code | Source | Author |
|---|---|---|
| পা.হ. | পাৰিজাত হৰণ | Sankaradeva |
| ৰু.হ. | ৰুক্মিণী হৰণ | Sankaradeva |
| ৰা.বি. | ৰাম বিজয় | Sankaradeva |
| কে.গো. | কেলি গোপাল | Sankaradeva |
| কী.ঘো. | কীৰ্তন ঘোষা | Sankaradeva |
| প.প্ৰ. | পত্নী প্ৰসাদ | Madhavadeva |
| চো.ধ. | চোৰ ধৰা | Madhavadeva |
| পি.গু. | পিম্পৰা গুচোৱা | Madhavadeva |
| ভৃ.হ. | ভূষণ হৰণ | Madhavadeva |
| অ.ভ./অ.ড. | অৰ্জুন ভঞ্জন | Madhavadeva |
| কা.দ. | কালী দমন | Madhavadeva |
| ভো.বে. | ভোজন বেহাৰ | Madhavadeva |
| ব.গী. | বৰগীত | both poets |
| ভ. | ভটিমা | praise-poem corpus |

---

## Running the tests

```bash
# v1 (no deps) — 18 cases
python3 lib/test_translate.py

# v2 (with NLP layer) — 9 cases
.venv/bin/python lib/test_translate_v2.py
```

All should print `passed`.

---

## Contributing

Highest-leverage gaps:

1. **Dictionary OCR coverage** — Goswami's source has 3,017 entries; the column-aware parser captures cleanly ~1,300. A better parser would recover the missing ~1,700.
2. **Roman-Assamese overrides** (`data/roman_overrides.json`) — every word added makes Roman input nicer.
3. **Heavier embedding fallback** — drop in `LaBSE` or `IndicBERTv2` in `lib/nlp.py` for users who want it. Keep the lightweight default.

PRs welcome.

---

## License

Code: yours to use freely. Linguistic data: digitised from Goswami's published 1990 work — please credit him.
