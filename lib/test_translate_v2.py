"""Tests for the v2 NLP-backed translator.

Run with the skill's venv:
    .venv/bin/python lib/test_translate_v2.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from translate_v2 import TranslatorV2


CASES_V2 = [
    # NLP-tokenizer cases (apostrophe preserved)
    ("তেওঁ ঘৰলৈ গ'ল",        "গেল",       "apostrophe-preserving tokenization"),

    # Sanskrit-synonym lookup (pre-mapped, no fuzzy needed)
    ("মোৰ চক্ষুত নীৰ আহিল", "আখিত",     "চক্ষু → আখি"),
    ("ৰাজাৰ মাথাত মুকুট",   "মাথে",     "মাথা → মাথ"),
    ("পবিত্ৰ গ্ৰন্থ",        "পুথি",     "গ্ৰন্থ → পুথি"),

    # Honest fallback: unknown technical words → biprokorṣa or unknown
    # (we don't claim to translate ফোন, কম্পিউটাৰ etc.)
    ("কম্পিউটাৰ আছে",       "আছি",       "modern term + verb"),

    # Long sentence
    ("মই কৃষ্ণৰ চৰণত শৰণ ললোঁ", "মঞি",  "long devotional sentence"),

    # All v1 cases must still pass
    ("মই",                   "মঞি",      "1sg core"),
    ("তোমাক",                "তোহাক",   "2sg acc"),
    ("Krishna",              "কৃষ্ণ",    "Roman name"),
]


def main() -> int:
    t = TranslatorV2()
    print(f"NLP status: {t.nlp_status()}")
    print()
    passes, failures = 0, []
    for inp, expected_substr, label in CASES_V2:
        r = t.translate(inp)
        if expected_substr in r['brajawali']:
            passes += 1
            print(f"  PASS  [{label:40}]  {inp!r:38} → {r['brajawali']!r}")
        else:
            failures.append((inp, expected_substr, r['brajawali'], label))
            print(f"  FAIL  [{label:40}]  {inp!r:38} → {r['brajawali']!r}  (want {expected_substr!r})")
    print()
    print(f"Result: {passes}/{len(CASES_V2)} passed, {len(failures)} failed")
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
