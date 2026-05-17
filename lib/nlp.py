"""NLP layer for v2 translator.

Two upgrades over v1:

  1. **indic-nlp-library** for proper Assamese tokenization + Unicode
     normalization (collapses ligature variants, chandra/dot variants etc.)

  2. **TF-IDF character-n-gram fuzzy match** for unknown Assamese stems —
     embeds every Assamese stem in our lexicon as a 3-5 char n-gram vector
     and finds the cosine-nearest match. Fast (<50 ms init, <1 ms query),
     no GPU, no 200 MB model download. Works because the questions we ask
     are: "what's the closest known Assamese root to *this unknown word*?"
     and Indic morphology is largely linear-affixal, so character n-grams
     capture stem similarity well.

Both layers are **optional** — if the deps aren't installed, the module
falls back to identity tokenization and disables fuzzy-match.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional

# ---- Tokenizer / Normalizer ------------------------------------------------

_normalizer = None
_tokenize_fn = None


def _init_indic_nlp():
    """Lazy-init indic-nlp-library; cache the normalizer & tokenizer."""
    global _normalizer, _tokenize_fn
    if _normalizer is not None or _tokenize_fn is not None:
        return
    try:
        from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
        from indicnlp.tokenize.indic_tokenize import trivial_tokenize
        factory = IndicNormalizerFactory()
        _normalizer = factory.get_normalizer('as')
        _tokenize_fn = lambda s: trivial_tokenize(s, lang='as')
    except ImportError:
        # Fallbacks: identity normalizer, regex tokenizer
        class _ID:
            def normalize(self, s): return s
        _normalizer = _ID()
        _tokenize_fn = lambda s: re.findall(r'\S+', s)


def normalize(text: str) -> str:
    _init_indic_nlp()
    return _normalizer.normalize(text)


def tokenize(text: str) -> list[str]:
    """Tokenize Assamese text. Returns list of word-tokens (no punctuation).
    Re-merges apostrophe-split tokens (e.g. গ + ' + ল → গ'ল)."""
    _init_indic_nlp()
    raw = list(_tokenize_fn(text))
    # Re-glue: <word> ' <word> → <word>'<word> (Assamese conjunct apostrophe)
    merged = []
    i = 0
    while i < len(raw):
        if i + 2 < len(raw) and raw[i + 1] == "'" and raw[i] and raw[i + 2]:
            merged.append(raw[i] + "'" + raw[i + 2])
            i += 3
            continue
        merged.append(raw[i])
        i += 1
    out = []
    for tok in merged:
        if re.match(r'^[\s।.,;:!?]+$', tok):
            continue
        out.append(tok)
    return out


def has_indic_nlp() -> bool:
    try:
        import indicnlp  # noqa
        return True
    except ImportError:
        return False


# ---- Fuzzy matcher (character-ngram TF-IDF) -------------------------------

_fuzzy_state: dict | None = None


def _build_fuzzy_index(lexicon_keys: list[str]):
    """Build TF-IDF char-ngram index over Assamese stems."""
    global _fuzzy_state
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
    except ImportError:
        _fuzzy_state = {'enabled': False}
        return

    vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), min_df=1)
    keys = list(lexicon_keys)
    if not keys:
        _fuzzy_state = {'enabled': False}
        return
    matrix = vec.fit_transform(keys)
    _fuzzy_state = {
        'enabled': True,
        'vec': vec,
        'matrix': matrix,
        'keys': keys,
        'cos': cosine_similarity,
        'np': np,
    }


def fuzzy_match(query: str, top_k: int = 3, threshold: float = 0.55) -> list[tuple[str, float]]:
    """Find top-K most similar Assamese stems to query. Empty list if disabled
    or no match above threshold."""
    if _fuzzy_state is None:
        return []
    if not _fuzzy_state.get('enabled'):
        return []
    vec = _fuzzy_state['vec']
    matrix = _fuzzy_state['matrix']
    keys = _fuzzy_state['keys']
    np = _fuzzy_state['np']
    cos = _fuzzy_state['cos']

    qv = vec.transform([query])
    sims = cos(qv, matrix)[0]
    if sims.size == 0:
        return []
    top_idx = np.argsort(sims)[::-1][:top_k]
    return [(keys[i], float(sims[i])) for i in top_idx if sims[i] >= threshold]


def init_fuzzy(lexicon_keys: list[str]):
    """Public entry: build the index from caller's lexicon."""
    _build_fuzzy_index(lexicon_keys)


def has_fuzzy() -> bool:
    return _fuzzy_state is not None and _fuzzy_state.get('enabled', False)


# ---- self-test ----

if __name__ == '__main__':
    import sys
    print('indic-nlp available:', has_indic_nlp())
    text = 'মই তোমাক ভাল পাওঁ৷ মোৰ চকুত পানী আহিল।'
    print('Normalized:', normalize(text))
    print('Tokenized: ', tokenize(text))

    # Fuzzy demo
    keys = ['চকু', 'মুখ', 'হাত', 'ভৰি', 'পানী', 'জুই', 'ঘৰ', 'কথা', 'ৰাজা',
            'মাথা', 'চুলি', 'কণ্ঠ', 'হৃদয়', 'বন্ধু', 'মাতৃ']
    init_fuzzy(keys)
    print('fuzzy enabled:', has_fuzzy())
    for q in ['চক্ষু', 'ঘৰৰ', 'মাথ', 'বুকু', 'বন্ধু', 'নৱনদী']:
        print(f'  fuzzy({q!r}) → {fuzzy_match(q, top_k=3, threshold=0.4)}')
