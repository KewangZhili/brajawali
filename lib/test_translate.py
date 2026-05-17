"""Smoke tests for the Brajawali translator. Run: python3 lib/test_translate.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from translate import Translator


CASES = [
    # (input, expected_substring_in_brajawali, comment)
    ("মই",                      "মঞি",       "1sg pronoun"),
    ("তুমি",                    "তোহো",      "2sg honorific"),
    ("তেওঁ",                    "তেহো",      "3sg neutral"),
    ("মোৰ",                     "হামাৰ",     "1sg gen"),
    ("তোমাক",                   "তোহাক",     "2sg acc"),
    ("চকু",                     "আখি",       "eye"),
    ("মুখ",                     "বদন",       "face"),
    ("পানী",                    "নীৰ",       "water"),
    ("জুই",                     "আগি",       "fire"),
    ("ঘৰ",                      "ঘৰ",        "house"),
    ("ভাল",                     "ভল্ল",       "good"),

    ("মই তোমাক ভাল পাওঁ",     "মঞি তোহাক ভল্ল",  "I love you"),
    ("তেওঁ ঘৰলৈ গ'ল",         "তেহো ঘৰকলাগি গেল",  "He went home"),
    ("ৰাম বনলৈ গ'ল",          "ৰাম বনকলাগি গেল",   "Ram went to forest"),
    ("কৃষ্ণৰ ভকত",            "কৃষ্ণক ভকত",         "Krishna's devotee (gen)"),

    # Roman input
    ("moi",                    "মঞি",      "Roman 1sg"),
    ("Krishna",                "কৃষ্ণ",     "Roman Krishna"),
    ("moi tumar logot",       "মঞি তোহাৰ সঙ্গে",  "Roman with-you"),
]


def main() -> int:
    t = Translator()
    passes, failures = 0, []
    for inp, expected_substr, label in CASES:
        result = t.translate(inp)
        actual = result['brajawali']
        if expected_substr in actual:
            passes += 1
            print(f"  PASS  [{label:30}]  {inp!r:35} → {actual!r}")
        else:
            failures.append((inp, expected_substr, actual, label))
            print(f"  FAIL  [{label:30}]  {inp!r:35} → {actual!r} (expected substring: {expected_substr!r})")
    print()
    print(f"Result: {passes}/{len(CASES)} passed, {len(failures)} failed")
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
