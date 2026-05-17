"""Assamese → Brajawali translator.

Pipeline:
   1. Normalise input (Roman → Assamese script if needed).
   2. Tokenise into morphological units (stem + case suffix; verb root + ending).
   3. For each token:
        a. exact lookup in core_lexicon (primary).
        b. exact lookup in OCR-parsed dictionary (secondary).
        c. stem stripping → lookup → re-attach Brajawali case suffix.
        d. apply biprokorṣa (cluster-breaking) heuristic.
        e. fallback: leave the Assamese word as-is, marked unknown.
   4. Re-assemble; supply citations where available.

Usage:
   from translate import Translator
   t = Translator()
   result = t.translate("মই তোমাক ভাল পাওঁ")
   print(result['brajawali'])
   print(result['alignment'])
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from collections import OrderedDict

try:
    from .transliterate import normalise_input, is_assamese_script
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from transliterate import normalise_input, is_assamese_script


_DATA = Path(__file__).resolve().parent.parent / 'data'


# ---- Assamese case suffixes (in order: longest first to win greedy matching) ----
ASM_CASE_SUFFIXES = [
    # (Assamese suffix, case_label)
    ('সকলক', 'pl_acc'), ('সকলে', 'pl_nom'), ('সকল', 'pl'),
    ('বোৰক', 'pl_acc'), ('বোৰৰ', 'pl_gen'), ('বোৰে', 'pl_nom'),
    ('বোৰত', 'pl_loc'), ('বোৰ', 'pl'),
    ('লোকে', 'pl_nom'), ('লোকক', 'pl_acc'),
    ('হঁতক', 'pl_acc'), ('হঁতৰ', 'pl_gen'), ('হঁতে', 'pl_nom'), ('হঁত', 'pl'),
    ('পৰা', 'abl'), ('লৈ', 'dat'), ('সৈতে', 'soc'),
    ('লগত', 'soc'),
    ('ৰে', 'inst'), ('ৰে', 'gen-mod'),
    ('েৰে', 'inst'), ('েৰ', 'inst'),
    ('ত', 'loc'),
    ('ৰ', 'gen'),
    ('ক', 'acc'),
    ('ই', 'nom'),
    ('এ', 'nom'),
]

# ---- Assamese verb endings (stem + ending = verb form). Map stem to Brajawali. ----
# Assamese verb morphology: stem + tense/person endings
ASM_VERB_ENDINGS = [
    # Continuous past (longest first)
    ('িছিলোঁ', 'past_cont_1sg'), ('িছিলো', 'past_cont_1sg'),
    ('িছিলা', 'past_cont_2sg'), ('িছিলে', 'past_cont_3sg'),
    ('ৈছিলোঁ', 'past_cont_1sg'), ('ৈছিলে', 'past_cont_3sg'),
    # Continuous present
    ('িছোঁ', 'pres_cont_1sg'), ('িছো', 'pres_cont_1sg'),
    ('িছা', 'pres_cont_2sg'), ('িছে', 'pres_cont_3sg'),
    ('ৈছোঁ', 'pres_cont_1sg'), ('ৈছো', 'pres_cont_1sg'),
    ('ৈছে', 'pres_cont_3sg'),
    # Past tense
    ('িলেহি', 'past_3sg_emph'),
    ('িলোঁ', 'past_1sg'), ('িলো', 'past_1sg'),
    ('িলে', 'past_3sg'), ('িলা', 'past_2sg'),
    ('িলি', 'past_2sg_inf'),
    ('লোঁ', 'past_1sg_alt'), ('লো', 'past_1sg_alt'),
    ('লে', 'past_3sg_alt'), ('লা', 'past_2sg_alt'),
    # Future
    ('িবলৈ', 'inf'),
    ('িবা', 'fut_2sg'), ('িবি', 'fut_2sg_inf'),
    ('িম', 'fut_1sg'), ('িব', 'fut_3sg'),
    # Habitual
    ('োঁ', 'hab_1sg'),
    ('ছা', 'pres_cont_2sg_short'),
    ('ছে', 'pres_cont_3sg_short'),
    ('ো', 'hab_1sg'),
    ('ে', 'hab_3sg'),
    ('া', 'hab_2sg_pol'),
    ('ই', 'hab_3sg_alt'),
    # Imperative
    ('ক', 'imp_pol'),
    # Conjunctive participle
    ('ি', 'conj_part'),
]

# Brajawali endings to substitute (idiomatic replacements)
BRAJ_ENDINGS = {
    'past_1sg':       'লো',
    'past_1sg_alt':   'লো',
    'past_2sg':       'লি',
    'past_2sg_alt':   'লি',
    'past_2sg_inf':   'লি',
    'past_3sg':       'ল',
    'past_3sg_alt':   'ল',
    'past_3sg_emph':  'লেহি',
    'pres_cont_1sg':  'ৈছি',
    'pres_cont_2sg':  'ৈছ',
    'pres_cont_2sg_short': 'য়',
    'pres_cont_3sg':  'ৈছে',
    'pres_cont_3sg_short': 'য়',
    'past_cont_1sg':  'ৈছিলো',
    'past_cont_2sg':  'ৈছিলা',
    'past_cont_3sg':  'ৈছিল',
    'hab_1sg':        'ো',
    'hab_2sg_pol':    'হ',
    'hab_3sg':        'য়',
    'hab_3sg_alt':    'য়',
    'fut_1sg':        'ব',
    'fut_2sg':        'বি',
    'fut_2sg_inf':    'বি',
    'fut_3sg':        'ব',
    'imp_pol':        'হ',
    'inf':            'ইতে',
    'conj_part':      'ি',
}

# Mapping Assamese case → Brajawali postposition (default first, alternates after)
BRAJ_CASE = {
    'nom':     [''],
    'acc':     ['ক', 'কু'],
    'inst':    ['এ', 'ৰে'],
    'dat':     ['কলাগি', 'লাগি'],
    'abl':     ['হন্তে', 'ত'],
    'gen':     ['ক', 'কেৰি', 'ৰ'],
    'loc':     ['ত', 'মহ'],
    'soc':     ['সঙ্গে', 'সাতে'],
    'pl':      ['সব'],
    'pl_nom':  ['সব'],
    'pl_acc':  ['সবক'],
    'pl_gen':  ['সবক', 'সবকেৰি'],
    'pl_loc':  ['সবত'],
}


# ---- biprokorṣa fallback rules — break Sanskrit clusters ----
BIPROKORSO_RULES = [
    (re.compile(r'গ্নি'), 'গনি'),    # অগ্নি → অগনি
    (re.compile(r'জ্ঞ'),   'গিয়'),   # অজ্ঞান → অগিয়ান
    (re.compile(r'স্হ'),   'থ'),     # স্হিৰ → থিৰ
    (re.compile(r'স্ত্'),  'ত'),
    (re.compile(r'স্ম'),   'সুম'),
    (re.compile(r'ক্ৰ'),   'কৰ'),
    (re.compile(r'প্ৰ'),   'পৰ'),
    (re.compile(r'প্ৰে'),  'পৰে'),
    (re.compile(r'প্ৰি'),  'পিৰি'),
    (re.compile(r'ক্ত'),   'কত'),
    (re.compile(r'ক্তি'),  'কতি'),
    (re.compile(r'র্থ'),   'ৰথ'),
    (re.compile(r'র্ম'),   'ৰম'),
    (re.compile(r'র্ণ'),   'ৰণ'),
    (re.compile(r'ক্ষ'),   'খ'),     # ক্ষীৰ → খীৰ
    (re.compile(r'র্ব'),   'ৰব'),
    (re.compile(r'র্য'),   'ৰ্য'),
    (re.compile(r'দ্ব'),   'দব'),
    (re.compile(r'ভ্ৰ'),   'ভৰ'),
    (re.compile(r'গ্ব'),   'গব'),
    (re.compile(r'ত্ত'),   'ত'),
    (re.compile(r'গ্ম'),   'গম'),
    (re.compile(r'ঙ্ক'),   'ঙ্ক'),
    (re.compile(r'ৰ্'),    'ৰ'),
    # র / ল interchange
    # final 'া' often dropped in Brajawali — e.g. কথা → কথ
]


def apply_biprokorso(s: str) -> str:
    """Apply phonological transformation rules for unknown words."""
    out = s
    for pat, repl in BIPROKORSO_RULES:
        out = pat.sub(repl, out)
    return out


# ---- main translator class ----

class Translator:
    def __init__(self):
        with (_DATA / 'core_lexicon.json').open(encoding='utf-8') as f:
            core = json.load(f)
        # Flatten the core lexicon to a single asm→[braja...] map
        self.core: dict[str, list[str]] = {}
        for section, mapping in core.items():
            if section.startswith('_'):
                continue
            for asm, brajas in mapping.items():
                if not isinstance(brajas, list):
                    continue
                self.core.setdefault(asm, []).extend(brajas)

        # OCR-parsed dictionary (inverted Assamese→Brajawali index)
        self.dict_idx: dict[str, list[dict]] = {}
        try:
            with (_DATA / 'dictionary.json').open(encoding='utf-8') as f:
                d = json.load(f)
                self.dict_idx = d.get('inverted', {})
        except FileNotFoundError:
            pass

        with (_DATA / 'grammar.json').open(encoding='utf-8') as f:
            self.grammar = json.load(f)

    # ---- lookups -----------------------------------------------------------

    def lookup(self, asm: str) -> tuple[list[str], str, str]:
        """Look up Assamese token → list of Brajawali alternatives.
        Returns (brajas, source_tag, citation)."""
        if asm in self.core:
            return self.core[asm], 'core', ''
        hits = self.dict_idx.get(asm)
        if hits:
            brajas = []
            citation = ''
            for h in hits:
                brajas.extend(h.get('brajawali', []))
                if not citation and h.get('citation'):
                    citation = h['citation']
            # Deduplicate
            seen = set()
            uniq = [b for b in brajas if not (b in seen or seen.add(b))]
            return uniq, 'dictionary', citation
        return [], 'unknown', ''

    # ---- morphological analysis -------------------------------------------

    def split_case_suffix(self, w: str) -> tuple[str, str | None]:
        """Try to split off an Assamese case-suffix from a noun-like word."""
        for suf, label in ASM_CASE_SUFFIXES:
            if w.endswith(suf) and len(w) > len(suf) + 1:
                stem = w[:-len(suf)]
                # Avoid breaking off too aggressively — stem must look like
                # a real Assamese stem (>= 2 chars, ends in non-suffix char)
                return stem, label
        return w, None

    def split_verb(self, w: str) -> tuple[str, str | None]:
        """Try to split off an Assamese verb ending."""
        for end, label in ASM_VERB_ENDINGS:
            if w.endswith(end) and len(w) > len(end):
                stem = w[:-len(end)]
                return stem, label
        return w, None

    # ---- verb-stem fallback table ----
    VERB_STEM_TO_BRAJA = {
        # Common Assamese verb stems (bare root form before any ending)
        # → preferred Brajawali base
        'কৰ': 'কৰ',
        'হ': 'হু',          # হ' → হু / হোই
        'যা': 'যা',
        'গ': 'গে',         # গ'ল = গেল
        'আহ': 'আই',        # আহিল = আইল
        'দ': 'দে',
        'ল': 'লে',
        'খা': 'খা',
        'দেখ': 'পেখ',
        'শুন': 'শুন',
        'জান': 'জান',
        'কাট': 'কাট',
        'পাঢ়': 'পঢ়',
        'লিখ': 'লিখ',
        'পঢ়': 'পঢ়',
        'বুজ': 'বুজ',
        'খেলা': 'খেলা',
        'নাচ': 'নাচ',
        'পাও': 'পাও',
        'পা': 'পা',
        'ভাব': 'চিন্ত',    # ভাবা → চিন্তা
        'মাৰ': 'মাৰ',
        'মৰ': 'মৰ',
        'ক': 'কহ',
        'বহ': 'বৈঠ',
        'ৰ': 'ৰহ',
        'উঠ': 'উঠ',
        'শো': 'শয়ন',
        'চা': 'পেখ',
        'চাই': 'পেখি',
        'চল': 'চল',
        'উৰ': 'উৰ',
        'বুল': 'বোল',
    }

    # ---- token translator -------------------------------------------------

    def translate_token(self, w: str) -> dict:
        """Translate one Assamese token. Returns dict with details."""
        # Direct lookup
        brajas, source, citation = self.lookup(w)
        if brajas:
            return {
                'asm': w,
                'braja': brajas[0],
                'alts': brajas[1:5],
                'source': source,
                'citation': citation,
                'analysis': 'direct',
            }

        # Try as verb form: stem + ending
        stem, ending = self.split_verb(w)
        if ending and stem:
            stem_brajas, src, cit = self.lookup(stem)
            # Try stem-table fallback
            if not stem_brajas and stem in self.VERB_STEM_TO_BRAJA:
                stem_brajas = [self.VERB_STEM_TO_BRAJA[stem]]
                src = 'verb_stem_table'
            # Try ending-extension stem (e.g. গ -> ind লৈছ -> stem 'গ')
            if not stem_brajas:
                alt_stem = stem.rstrip('িয়াাই')
                if alt_stem and alt_stem != stem:
                    stem_brajas, src, cit = self.lookup(alt_stem)
                    if not stem_brajas and alt_stem in self.VERB_STEM_TO_BRAJA:
                        stem_brajas = [self.VERB_STEM_TO_BRAJA[alt_stem]]
                        src = 'verb_stem_table'
            if stem_brajas:
                braj_end = BRAJ_ENDINGS.get(ending, '')
                base = stem_brajas[0]
                # Strip imperative হ/হ্‌ at end of citation form
                base_clean = re.sub(r'হ$', '', base)
                braja = base_clean + braj_end
                return {
                    'asm': w,
                    'braja': braja,
                    'alts': [b + braj_end for b in stem_brajas[1:4]],
                    'source': f'{src}+morph',
                    'citation': cit,
                    'analysis': f'verb stem={stem} ending={ending}',
                }

        # Try as noun form: stem + case suffix
        stem, case = self.split_case_suffix(w)
        if case and stem:
            stem_brajas, src, cit = self.lookup(stem)
            if stem_brajas:
                base = stem_brajas[0]
                # Pick a Brajawali case suffix
                braj_suffix = BRAJ_CASE.get(case, [''])[0]
                braja = base + braj_suffix
                alts = [b + braj_suffix for b in stem_brajas[1:4]]
                return {
                    'asm': w,
                    'braja': braja,
                    'alts': alts,
                    'source': f'{src}+morph',
                    'citation': cit,
                    'analysis': f'noun stem={stem} case={case}',
                }

        # Last resort: phonological transformation
        transformed = apply_biprokorso(w)
        if transformed != w:
            return {
                'asm': w,
                'braja': transformed,
                'alts': [],
                'source': 'biprokorso',
                'citation': '',
                'analysis': 'phonological-fallback',
            }

        # Unknown — return as-is
        return {
            'asm': w,
            'braja': w,
            'alts': [],
            'source': 'unknown',
            'citation': '',
            'analysis': 'no-match',
        }

    # ---- sentence-level ---------------------------------------------------

    def tokenise(self, text: str) -> list[str]:
        """Split into Assamese word-tokens preserving punctuation."""
        return re.findall(r'\S+|[\s।.,;:!?]', text)

    def translate(self, text: str) -> dict:
        """Translate a sentence/paragraph from Assamese (or Roman) to Brajawali."""
        # Step 1: normalise input
        original = text
        normalised = normalise_input(text)

        # Step 2: tokenise & translate
        result_tokens: list[dict] = []
        out_words: list[str] = []
        for tok in self.tokenise(normalised):
            if re.match(r'^[\s।.,;:!?]+$', tok):
                out_words.append(tok)
                continue
            # Strip leading/trailing punctuation from tok for translation
            m = re.match(r'^([।.,;:!?\s]*)(.+?)([।.,;:!?\s]*)$', tok)
            if not m:
                out_words.append(tok); continue
            lead, core, trail = m.groups()
            res = self.translate_token(core)
            result_tokens.append(res)
            out_words.append(lead + res['braja'] + trail)

        return {
            'input': original,
            'normalised_assamese': normalised,
            'brajawali': ' '.join(' '.join(out_words).split()),
            'alignment': result_tokens,
            'metadata': {
                'token_count': len(result_tokens),
                'unknown_count': sum(1 for r in result_tokens if r['source'] == 'unknown'),
                'morph_count': sum(1 for r in result_tokens if 'morph' in r['source']),
                'biprokorso_count': sum(1 for r in result_tokens if r['source'] == 'biprokorso'),
                'direct_count': sum(1 for r in result_tokens if r['source'] in ('core', 'dictionary')),
            },
        }


# ---- CLI demo ----

def _demo():
    t = Translator()
    samples = [
        "মই তোমাক ভাল পাওঁ",
        "তেওঁ ঘৰলৈ গ'ল",
        "মোৰ চকুত পানী আহিল",
        "Krishna nile dhanu",
        "moi tumar logot ahisilo",
        "ৰাম বনলৈ গ'ল",
        "তুমি কি কৰিছা",
    ]
    for s in samples:
        r = t.translate(s)
        print(f"INPUT     : {s}")
        print(f"NORMALISED: {r['normalised_assamese']}")
        print(f"BRAJAWALI : {r['brajawali']}")
        print(f"  meta    : {r['metadata']}")
        for tok in r['alignment']:
            print(f"    {tok['asm']:20} → {tok['braja']:20} [{tok['source']}: {tok['analysis']}]")
        print()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        text = ' '.join(sys.argv[1:])
        t = Translator()
        r = t.translate(text)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        _demo()
