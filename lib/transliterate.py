"""Roman → Assamese script transliterator.

Designed for the way Assamese speakers actually type in Roman: 'o' = অ
(the inherent vowel), 'oi' = ঐ (diphthong), 'au' = ঔ, doubled letters
mark long vowels (aa = আ, ii = ঈ). This is closer to what people use on
Facebook/WhatsApp than strict ITRANS.

Conventions used:
   o    অ (implicit/inherent — bare consonant has it built in)
   a    আ (sometimes)        aa is more reliable
   aa   আ
   i    ই            ii  ঈ
   u    উ            uu  ঊ
   e    এ
   oi   ঐ
   ou   ও            au  ঔ
   M    ং            ~  ঁ
   H    ঃ

   k g j t d n p b m l s h are themselves
   kh gh ch chh jh Th Dh th dh ph bh sh ng Ny  → conjuncts
   r → ৰ   w/v → ৱ   y → য

The strategy: tokenise the word into (consonant?, vowel?) pairs greedily,
left-to-right, and emit Assamese script accordingly.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

_OVERRIDES: dict[str, str] | None = None


def _load_overrides() -> dict[str, str]:
    global _OVERRIDES
    if _OVERRIDES is None:
        path = Path(__file__).resolve().parent.parent / 'data' / 'roman_overrides.json'
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            _OVERRIDES = {k: v for k, v in data.items() if not k.startswith('_')}
        except FileNotFoundError:
            _OVERRIDES = {}
    return _OVERRIDES

# ---- vowel inventory ----
# When NOT preceded by a consonant, write the independent letter.
# When preceded by a consonant, emit the matra (dependent form).
INDEP_VOWELS = {
    'a':  'অ',    # bare 'a' often = অ when independent (e.g. 'arjuna' = অৰ্জুন)
    'aa': 'আ',
    'i':  'ই',  'ii': 'ঈ',
    'u':  'উ',  'uu': 'ঊ',
    'e':  'এ',  'ai': 'ঐ', 'oi': 'ঐ',
    'o':  'অ',  'ou': 'ও',  'O': 'ও',  'au': 'ঔ',
    'ri': 'ঋ',
}

MATRA = {
    'a':  '',          # inherent
    'aa': 'া',
    'i':  'ি',  'ii': 'ী',
    'u':  'ু',  'uu': 'ূ',
    'e':  'ে',  'ai': 'ৈ', 'oi': 'ৈ',
    'o':  '',           # inherent (default)
    'ou': 'ো',  'O': 'ো',  'au': 'ৌ',
    'ri': 'ৃ',
}

# Order matters: longest first
VOWEL_KEYS = ['aa', 'ii', 'uu', 'oi', 'ai', 'ou', 'au', 'ri',
              'a', 'i', 'u', 'e', 'o', 'O']

CONSONANTS_ORDER = [
    ('ksh', 'ক্ষ'), ('Ksh', 'ক্ষ'),
    ('kh', 'খ'),   ('gh', 'ঘ'),
    ('chh', 'ছ'),  ('Ch', 'ছ'),  ('ch', 'চ'),
    ('jh', 'ঝ'),
    ('Th', 'ঠ'),   ('Dh', 'ঢ'),
    ('th', 'থ'),   ('dh', 'ধ'),
    ('ph', 'ফ'),   ('bh', 'ভ'),
    ('sh', 'শ'),   ('Sh', 'ষ'),
    ('ng', 'ঙ'),
    ('Ny', 'ঞ'),   ('GY', 'জ্ঞ'),
    ('w',  'ৱ'),   ('v',  'ৱ'),  ('y', 'য'),
    ('k',  'ক'),   ('g',  'গ'),  ('j', 'জ'),
    ('T',  'ট'),   ('D',  'ড'),  ('N', 'ণ'),
    ('t',  'ত'),   ('d',  'দ'),  ('n', 'ন'),
    ('p',  'প'),   ('b',  'ব'),  ('m', 'ম'),
    ('r',  'ৰ'),   ('R',  'ৰ'),  ('l', 'ল'),
    ('s',  'স'),
    ('h',  'হ'),
    ('x',  'ক্ষ'),
]

ANUSVARA, CANDRABINDU, VISARGA, HASANTA = 'ং', 'ঁ', 'ঃ', '্'


def is_assamese_script(s: str) -> bool:
    asm = sum(1 for c in s if 'ঀ' <= c <= '৿')
    return asm > 0 and asm / max(len(s), 1) >= 0.4


def _match_vowel(s: str, i: int):
    for k in VOWEL_KEYS:
        if s[i:i+len(k)] == k:
            return k, len(k)
    return None


def _match_consonant(s: str, i: int):
    for key, glyph in CONSONANTS_ORDER:
        if s[i:i+len(key)] == key:
            return key, glyph, len(key)
    return None


def transliterate_word(word: str) -> str:
    """Transliterate one Roman word into Assamese script.

    Algorithm: walk left-to-right. State `last_consonant_idx` records the
    last position in the output that was a bare consonant glyph (so we can
    join it to the next consonant via halant when no vowel intervened).
    """
    out: list[str] = []
    i = 0
    pending_consonant = False   # did we just emit a consonant + inherent 'a'?

    # special case: if word starts with vowel only
    while i < len(word):
        ch = word[i]

        if ch == 'M':
            out.append(ANUSVARA); i += 1; pending_consonant = False; continue
        if ch == '~':
            out.append(CANDRABINDU); i += 1; continue
        if ch == 'H' and i > 0 and not _match_vowel(word, i+1):
            out.append(VISARGA); i += 1; continue

        # try consonant first (greedy), as it's often shape-distinctive
        c = _match_consonant(word, i)
        if c:
            ckey, cglyph, clen = c
            j = i + clen
            # Look ahead for vowel
            v = _match_vowel(word, j)
            if pending_consonant:
                # We need a halant before this new consonant
                out.append(HASANTA)
                out.append(cglyph)
            else:
                out.append(cglyph)
            if v:
                vk, vlen = v
                m = MATRA.get(vk, '')
                if m:
                    out.append(m)
                # else: inherent vowel, no matra appended
                i = j + vlen
                pending_consonant = False
            else:
                # End-of-word or another consonant follows
                # If end-of-word, suppress inherent vowel by appending halant?
                # Convention: in Assamese script, end-consonants normally do
                # NOT have explicit halant. We'll keep them as-is.
                i = j
                pending_consonant = True
            continue

        # vowel without preceding consonant
        v = _match_vowel(word, i)
        if v:
            vk, vlen = v
            out.append(INDEP_VOWELS.get(vk, vk))
            i += vlen
            pending_consonant = False
            continue

        # passthrough
        out.append(ch)
        i += 1
        pending_consonant = False

    return ''.join(out)


def roman_to_assamese(text: str) -> str:
    overrides = _load_overrides()
    # Try multi-word phrase override first
    lower = text.lower().strip()
    if lower in overrides:
        return overrides[lower]

    parts = re.split(r'(\s+|[।\.,;:!?\-–—\(\)\[\]"\'])', text)
    out = []
    for p in parts:
        if not p:
            continue
        if re.match(r'^[\s।\.,;:!?\-–—\(\)\[\]"\']+$', p):
            out.append(p)
        elif re.match(r'^[A-Za-z~]+$', p):
            # word-level override (case-insensitive)
            o = overrides.get(p) or overrides.get(p.lower())
            if o:
                out.append(o)
            else:
                out.append(transliterate_word(p))
        else:
            out.append(p)
    return ''.join(out)


def normalise_input(text: str) -> str:
    if is_assamese_script(text):
        return text
    return roman_to_assamese(text)


if __name__ == '__main__':
    samples = [
        "moi",
        "tumi",
        "ghor",
        "monuh",
        "moi tumar logot ahisilo",
        "moi tumar logot ahisilou",
        "kotha kou",
        "Krishna",
        "namaskar",
        "এতিয়া কি কৰিছা",
        "moi gham",
        "tumi kio aha nai",
        "tumar nam ki",
    ]
    for s in samples:
        print(f"{s!r:50}  →  {normalise_input(s)!r}")
