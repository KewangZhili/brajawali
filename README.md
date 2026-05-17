# Brajawali

Translate modern Assamese (or Roman-Assamese) into **Brajawali** — the literary language of Srimanta Sankaradeva and Madhavadeva used in *Ankiya Nat*, *Borgeet*, and *Bhātimā* (c. 1481–1568 CE).

```bash
python3 lib/translate.py "মই তোমাক ভাল পাওঁ"
# → মঞি তোহাক ভল্ল পাও
```

That's it. Works offline. No model weights, no API calls — just a grammar, a dictionary, and rules.

---

## Why this exists

Brajawali (also written Brajbuli) is a *constructed* literary language — a stylised mix of Maithili, Sanskrit, Assamese, and Avahaṭṭha that the Vaishnavite saint-poets of Assam used for their plays and devotional songs starting 1481 CE. There is **one** systematic reference work for it: Sri Sri Narayan Chandra Goswami's *ব্ৰজাৱলী ভাষাৰ ব্যাকৰণ আৰু অভিধান* (Lawyer's Book Stall, Guwahati, 1990).

This project is a complete digital implementation of that reference: a working grammar engine, a structured dictionary, and a translator that takes either an Assamese sentence or a Roman-Assamese sentence and produces a faithful Brajawali rendering, with token-level provenance back to the source.

---

## Quick start

### As a Claude Code skill

Drop the directory into `~/.claude/skills/brajawali/`. Claude auto-discovers it.

```
You: translate to brajawali — তুমি ক'ত গৈছিলা
Claude: তোহো কথি গৈছিলা
```

### As a CLI

```bash
git clone https://github.com/KewangZhili/brajawali.git
cd brajawali
python3 lib/translate.py "তেওঁ ঘৰলৈ গ'ল"
```

Output:

```json
{
  "input": "তেওঁ ঘৰলৈ গ'ল",
  "normalised_assamese": "তেওঁ ঘৰলৈ গ'ল",
  "brajawali": "তেহো ঘৰকলাগি গেল",
  "alignment": [
    {"asm": "তেওঁ",   "braja": "তেহো",        "source": "core"},
    {"asm": "ঘৰলৈ",   "braja": "ঘৰকলাগি",     "source": "core+morph", "analysis": "noun stem=ঘৰ case=dat"},
    {"asm": "গ'ল",    "braja": "গেল",          "source": "core"}
  ]
}
```

### Roman input works too

```bash
python3 lib/translate.py "moi tumar logot ahisilo"
# → মঞি তোহাৰ সঙ্গে আৱৈছিলো
```

The transliterator auto-detects script. ITRANS-style with sensible Assamese conventions: `moi`=মই, `tumi`=তুমি, `ghor`=ঘৰ, `monuh`=মানুহ.

---

## Examples

| Modern Assamese | Brajawali |
|---|---|
| মই তোমাক ভাল পাওঁ | মঞি তোহাক ভল্ল পাও |
| তেওঁ ঘৰলৈ গ'ল | তেহো ঘৰকলাগি গেল |
| মোৰ চকুত পানী আহিল | হামাৰ আখিত নীৰ আইল |
| ৰাম বনলৈ গ'ল | ৰাম বনকলাগি গেল |
| কৃষ্ণৰ ভকত | কৃষ্ণক ভকত |
| তুমি কি কৰিছা | তোহো কী কৰৈছ |
| `Krishna nile dhanu` | কৃষ্ণ নৱল শৰাসন |
| `moi tumar logot ahisilo` | মঞি তোহাৰ সঙ্গে আৱৈছিলো |

---

## How it works

For each token:

1. **Direct lookup** in the curated core lexicon (~600 high-frequency Assamese↔Brajawali pairs by semantic field — pronouns, kinship, body, nature, abstracts, verbs, particles)
2. **Dictionary fallback** in the OCR-parsed dictionary (~700 entries with citations to source texts)
3. **Morphological split**:
   - Noun forms: split off Assamese case suffix (`-ত`, `-ৰ`, `-লৈ`, `-পৰা`), look up the stem, attach the equivalent Brajawali case (`-ত`, `-ক`/`-কেৰি`, `-কলাগি`, `-হন্তে`)
   - Verb forms: split off Assamese ending (`-িলোঁ`, `-িছা`, `-িব`), look up the stem, attach the equivalent Brajawali ending (`-লো`, `-য়`, `-ব`)
4. **Biprokorṣa fallback** — applies the documented phonological rules from Goswami's Chapter 2-ঘ:
   - `গ্নি → গনি` (অগ্নি → অগনি)
   - `স্হ → থ` (স্হিৰ → থিৰ)
   - `ক্ষ → খ` (ক্ষীৰ → খীৰ)
   - `ৰ ↔ ল` interchange (নাবোৰ ↔ নাবোল)
   - …and ~110 more
5. **Unknown** — passes the Assamese word through unchanged and flags it

Every translation is **traceable**: the JSON output tells you which path produced each token.

---

## Architecture

```
brajawali/
├── SKILL.md                  # Claude Code skill manifest
├── README.md                 # this file
├── data/
│   ├── grammar.json          # pronouns, 7-case suffixes, 9 verb classes,
│   │                         # 16 prefixes, ~110 biprokorṣa rules,
│   │                         # source-citation codes
│   ├── core_lexicon.json     # ~600 hand-curated Assamese ↔ Brajawali
│   ├── dictionary.json       # ~700 OCR-parsed dictionary entries with citations
│   └── roman_overrides.json  # Roman-Assamese spelling fast-path
└── lib/
    ├── transliterate.py      # Roman → Assamese script converter
    ├── translate.py          # main translation engine
    ├── parse_dict.py         # rebuilds dictionary.json from raw OCR
    └── test_translate.py     # 18 smoke tests, all passing
```

No external dependencies — pure Python 3.10+.

---

## Linguistic notes

A few things that make Brajawali different from modern Assamese:

- **Pronouns are gender-neutral**. `তেহো` covers both "he" and "she". `তোহো` covers all three honorific levels (তই/তুমি/আপুনি).
- **No passive voice**. Only `kartṛ-vāchya` (active) is attested.
- **No neuter gender**. Only masculine and feminine.
- **Plural is periphrastic**. Built with `সব`, `সকল`, `গণ`, `নিকৰয়ে` rather than a suffix.
- **Genitive is `-ক / -কেৰি`** (not Assamese `-ৰ`); dative-locative is `-কলাগি` / `-মহ`.
- **Verb endings start with `-ল-`** for past (`কয়ল` = "(he) said"), `-ব` for future (`কৰব` = "will do"), `-হ` for polite imperative (`কৰহ` = "please do").
- **Sanskrit clusters dissolve** via *biprokorṣa* — every বুদ্ধি becomes বুধি, every প্ৰভু becomes পহু, every ভক্তি becomes ভকতি.

The `data/grammar.json` file is your reference for all of these — readable and well-commented.

---

## What this is NOT

- **Not a language model.** It's a deterministic rule + lookup system. Same input always gives the same output.
- **Not exhaustive.** Brajawali is a *closed historical corpus* (~3,017 words in Goswami's full dictionary). Modern Assamese terms (ফোন, কম্পিউটাৰ, ৰেলগাড়ী) have no Brajawali equivalent. The system flags those as unknown rather than inventing.
- **Not poetic.** It preserves Assamese word order. Re-arranging into idiomatic Borgeet metre/rhyme is a separate art.

---

## Source

Sri Sri Narayan Chandra Goswami, *ব্ৰজাৱলী ভাষাৰ ব্যাকৰণ আৰু অভিধান* ("Grammar and Dictionary of the Brajawali Language"), Lawyer's Book Stall, Guwahati, June 1990. 332 pages. Foreword by Dr. Maheswar Neog.

Author plate dates the manuscript to 1985 Saka. The grammar and dictionary together took the author 1 year and 5 months to compile (March 1985 – August 1986). Dr. Maheswar Neog convinced him to include the grammar; the original commission was for the dictionary alone.

The PDF used as input: 332-page scanned image (16.7 MB), OCRed at 300 DPI with Tesseract using the Assamese (`asm`) language model. Full OCR text retained for reproducibility; parser at `lib/parse_dict.py` extracts structured entries.

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

## Contributing

The biggest gap is the OCR-parsed dictionary — Goswami's source has 3,017 entries, but the two-column scan layout means my parser captures cleanly ~700. A column-aware re-parse would recover the missing ~2,300. Pull requests welcome.

The other obvious extension is the Roman-Assamese override list — `data/roman_overrides.json` has ~80 spellings; the more it has, the better the Roman-input experience.

---

## Running the tests

```bash
python3 lib/test_translate.py
```

Should print `18/18 passed`.

---

## License

This is an academic/personal project built around an out-of-print 1990 reference book. Code is yours to use. The linguistic data is digitised from Goswami's published work; respect the original author's scholarship by attributing him.
