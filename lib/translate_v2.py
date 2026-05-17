"""Brajawali translator v2 — NLP-backed.

Adds two layers on top of v1's deterministic engine:

  * Layer 1: indic-nlp-library tokenizer + Unicode normalizer
  * Layer 4: TF-IDF char-ngram fuzzy matcher (sklearn) for semantic
             fallback on unknown Assamese stems

Both are *optional* — when their deps are missing, v2 transparently
falls back to v1 behaviour.

Pipeline:
    Roman → Assamese script
        ↓
    indic-nlp normalize + tokenize
        ↓
    Per token:
        1. direct lookup (core lexicon → dictionary)
        2. morphological split (case suffix / verb ending)
        3. lookup of stem
        4. NEW: fuzzy match unknown stem → nearest known stem
        5. biprokorṣa phonological fallback
        6. unknown → pass through

Token-level provenance ('source' field) tells you which path produced
each token: core / dictionary / core+morph / fuzzy / biprokorso / unknown.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from transliterate import normalise_input, is_assamese_script  # noqa
from translate import (Translator as _V1Translator, BRAJ_ENDINGS, BRAJ_CASE,
                       ASM_CASE_SUFFIXES, ASM_VERB_ENDINGS, apply_biprokorso)
import nlp


_DATA = Path(__file__).resolve().parent.parent / 'data'


class TranslatorV2(_V1Translator):
    """v1 translator with NLP-backed fallback layers."""

    def __init__(self, fuzzy_threshold: float = 0.45):
        super().__init__()
        self.fuzzy_threshold = fuzzy_threshold
        # Build the fuzzy index over every Assamese stem we know
        # (core lexicon + dictionary inverted index).
        all_stems = set(self.core.keys()) | set(self.dict_idx.keys())
        nlp.init_fuzzy(sorted(all_stems))

    # ---- override: smart tokenisation -------------------------------------

    def tokenise(self, text: str) -> list[str]:
        if nlp.has_indic_nlp():
            text = nlp.normalize(text)
            toks = nlp.tokenize(text)
            return toks
        return super().tokenise(text)

    # ---- new: fuzzy fallback ----------------------------------------------

    def fuzzy_translate_token(self, w: str, threshold: float | None = None) -> dict | None:
        """Use char-ngram TF-IDF to find the nearest known stem; if it's
        confident enough, return its Brajawali rendering."""
        if not nlp.has_fuzzy():
            return None
        thresh = threshold if threshold is not None else self.fuzzy_threshold
        candidates = nlp.fuzzy_match(w, top_k=5, threshold=thresh)
        if not candidates:
            return None
        for cand_stem, sim in candidates:
            brajas, src, cit = self.lookup(cand_stem)
            if brajas:
                return {
                    'asm': w,
                    'braja': brajas[0],
                    'alts': brajas[1:5],
                    'source': 'fuzzy',
                    'citation': cit,
                    'analysis': f'fuzzy nearest={cand_stem!r} sim={sim:.3f}',
                    'fuzzy_score': sim,
                }
        return None

    # ---- override: token translator ---------------------------------------

    def translate_token(self, w: str) -> dict:
        """v2 pipeline: direct lookup → morph split → fuzzy → biprokorṣa → unknown."""
        # 1. direct lookup
        brajas, source, citation = self.lookup(w)
        if brajas:
            return {
                'asm': w, 'braja': brajas[0], 'alts': brajas[1:5],
                'source': source, 'citation': citation, 'analysis': 'direct',
            }

        # 2. verb-form morphology
        stem, ending = self.split_verb(w)
        if ending and stem:
            stem_brajas, src, cit = self.lookup(stem)
            if not stem_brajas and stem in self.VERB_STEM_TO_BRAJA:
                stem_brajas = [self.VERB_STEM_TO_BRAJA[stem]]
                src = 'verb_stem_table'
            if not stem_brajas:
                alt_stem = stem.rstrip('িয়াাই')
                if alt_stem and alt_stem != stem:
                    stem_brajas, src, cit = self.lookup(alt_stem)
                    if not stem_brajas and alt_stem in self.VERB_STEM_TO_BRAJA:
                        stem_brajas = [self.VERB_STEM_TO_BRAJA[alt_stem]]
                        src = 'verb_stem_table'
            if stem_brajas:
                braj_end = BRAJ_ENDINGS.get(ending, '')
                base = re.sub(r'হ$', '', stem_brajas[0])
                return {
                    'asm': w, 'braja': base + braj_end,
                    'alts': [b + braj_end for b in stem_brajas[1:4]],
                    'source': f'{src}+morph', 'citation': cit,
                    'analysis': f'verb stem={stem} ending={ending}',
                }

        # 3. noun case morphology
        stem, case = self.split_case_suffix(w)
        if case and stem:
            stem_brajas, src, cit = self.lookup(stem)
            if stem_brajas:
                base = stem_brajas[0]
                braj_suffix = BRAJ_CASE.get(case, [''])[0]
                return {
                    'asm': w, 'braja': base + braj_suffix,
                    'alts': [b + braj_suffix for b in stem_brajas[1:4]],
                    'source': f'{src}+morph', 'citation': cit,
                    'analysis': f'noun stem={stem} case={case}',
                }

        # 4. NLP fuzzy fallback (NEW — comes BEFORE biprokorṣa)
        fz = self.fuzzy_translate_token(w)
        if fz:
            return fz

        # 4b. fuzzy on stripped stem
        for suf, label in ASM_CASE_SUFFIXES + ASM_VERB_ENDINGS:
            if w.endswith(suf) and len(w) > len(suf) + 1:
                stem = w[:-len(suf)]
                fz = self.fuzzy_translate_token(stem)
                if fz:
                    # Apply the case marker if it was a noun suffix
                    suffix_extra = ''
                    case_brajas = BRAJ_CASE.get(label)
                    if case_brajas:
                        suffix_extra = case_brajas[0]
                    fz['braja'] = fz['braja'] + suffix_extra
                    fz['analysis'] = f"fuzzy(stem={stem!r}) [{fz['analysis']}] +case={label}"
                    return fz

        # 5. biprokorṣa phonological fallback
        bp = apply_biprokorso(w)
        if bp != w:
            return {
                'asm': w, 'braja': bp, 'alts': [],
                'source': 'biprokorso', 'citation': '',
                'analysis': 'phonological-fallback',
            }

        # 6. unknown
        return {
            'asm': w, 'braja': w, 'alts': [],
            'source': 'unknown', 'citation': '',
            'analysis': 'no-match',
        }

    # ---- helper: report what NLP layers are active -----------------------

    def nlp_status(self) -> dict:
        return {
            'indic_nlp_available': nlp.has_indic_nlp(),
            'fuzzy_index_built': nlp.has_fuzzy(),
            'lexicon_size': len(self.core) + len(self.dict_idx),
        }


def _demo():
    t = TranslatorV2()
    print('NLP status:', t.nlp_status())
    print()

    samples = [
        ("মই তোমাক ভাল পাওঁ", "v1 — basics"),
        ("তেওঁ ঘৰলৈ গ'ল",     "v1 — directional"),
        ("মোৰ চক্ষুত নীৰ আহিল", "v2 — Sanskritised input (চক্ষু→চকু→আখি)"),
        ("ৰাজাৰ মাথাত মুকুট", "v2 — মাথা→মাথ"),
        ("বন্ধু আহিল",        "v1 — has বন্ধু in lexicon"),
        ("পবিত্ৰ গ্ৰন্থ",     "v2 — গ্ৰন্থ unknown, fuzzy?"),
        ("Krishna nile dhanu", "v1 — Roman"),
        ("আজি অতি সুন্দৰ দিন", "mixed"),
    ]
    for text, label in samples:
        r = t.translate(text)
        print(f"[{label}]")
        print(f"  IN : {text}")
        print(f"  OUT: {r['brajawali']}")
        for tok in r['alignment']:
            extra = f" sim={tok['fuzzy_score']:.2f}" if 'fuzzy_score' in tok else ''
            print(f"     {tok['asm']:18} → {tok['braja']:18} [{tok['source']}{extra}]")
        print()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        text = ' '.join(sys.argv[1:])
        t = TranslatorV2()
        print(json.dumps(t.translate(text), ensure_ascii=False, indent=2))
    else:
        _demo()
