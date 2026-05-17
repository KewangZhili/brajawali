"""Parse the OCR'd Brajawali dictionary into structured entries.

Strategy:
  1. Walk the dictionary section line by line.
  2. Carry a buffer of "pending headwords" — Assamese-only short lines that
     precede entries (the left column).
  3. When we see a line that contains "(POS-tag)", treat that line + any
     following continuation lines (until the next entry-trigger) as ONE
     entry whose head set = pending_heads + any inline head before "(POS)".
  4. Continuation lines: any line that is NOT itself a new entry start AND
     NOT a pure orphan headword.
"""
import re
import json
import sys
from pathlib import Path

POS_TAGS = {
    'বি': 'noun', 'বিণ': 'adjective', 'বিপ': 'adjective',
    'অবা': 'indeclinable', 'অব্য': 'indeclinable', 'অব্যয়': 'indeclinable',
    'বা.সর্ব': 'pronoun', 'বা,সর্ব': 'pronoun',
    'ব্য.সর্ব': 'pronoun', 'ব্য,সর্ব': 'pronoun',
    'বা.সৰ্ব': 'pronoun', 'বা,সৰ্ব': 'pronoun',
    'ব্য.সৰ্ব': 'pronoun', 'ব্য,সৰ্ব': 'pronoun',
    'কা.সৰ্ব': 'pronoun', 'কা,সৰ্ব': 'pronoun',
    'কা.সর্ব': 'pronoun', 'কা,সর্ব': 'pronoun',
    'স্হা.সর্ব': 'pronoun', 'স্থা.সর্ব': 'pronoun',
    'স্হা.সৰ্ব': 'pronoun',
    'স.ধা': 'verb_root', 'স,ধা': 'verb_root',
    'অস.ক্রি': 'verb_nonfinite', 'অস,ক্রি': 'verb_nonfinite',
    'অসংক্রি': 'verb_nonfinite', 'অসংক্ৰি': 'verb_nonfinite',
    'অসং,ক্রি': 'verb_nonfinite', 'অসং,ক্ৰি': 'verb_nonfinite',
    'অসংফ্লি': 'verb_nonfinite', 'অস.ষ্কি': 'verb_nonfinite', 'অস,ষ্কি': 'verb_nonfinite',
    'সংঅস.ক্ৰি': 'verb_nonfinite', 'সংঅস,ক্ৰি': 'verb_nonfinite',
    'সং,অস,ক্ৰি': 'verb_nonfinite', 'সং,অসংফ্রি': 'verb_nonfinite',
    'অনু,দ্বি.পু': 'verb_imperative',
    'ক্রি': 'verb', 'ক্ৰি': 'verb',
    'ক্রি.প্ৰ.পু': 'verb', 'ক্রি.দ্বি.পু': 'verb', 'ক্রি.তৃ.পু': 'verb',
    'ক্রি.বিণ': 'adverb', 'ক্ৰি.বিণ': 'adverb',
    'ক্লি.বিণ': 'adverb', 'ফ্ৰি.বিণ': 'adverb',
    'কৃদ.বিণ': 'adverb', 'কৃদ,বিণ': 'adverb',
    'ভা.অব্য': 'interjection', 'ভা.অবা': 'interjection',
    'সম্বো.অব্য': 'vocative', 'সম্বো.অবা': 'vocative',
    'অনুকা': 'echo', 'অনুরূ': 'reduplicative',
    'বি.প': 'noun',
    'বি.স্ত্রী': 'noun_fem', 'বি.স্মীং': 'noun_fem', 'বি.স্দীং': 'noun_fem',
    'বিণ.স্মীং': 'adjective_fem', 'বিণ.স্দীং': 'adjective_fem',
}


def is_assamese(s: str, frac: float = 0.5) -> bool:
    if not s:
        return False
    asm = sum(1 for c in s if 'ঀ' <= c <= '৿')
    return asm > 0 and asm / max(len(s), 1) >= frac


def clean_text(s: str) -> str:
    s = re.sub(r'[\x00-\x1f]', ' ', s)
    s = s.replace('৷', '।')
    s = re.sub(r'[_‐]+', '-', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip(' .,;।')


def looks_like_pos(s: str) -> bool:
    s = re.sub(r'\s+', '', s).rstrip('.,।)')
    if not s or len(s) > 24:
        return False
    if not is_assamese(s, 0.5):
        return False
    stems = ['বি', 'বিণ', 'অব', 'ক্রি', 'ক্ৰি', 'ক্লি', 'ফ্ৰি', 'ধা', 'অনু',
             'সম্বো', 'ভা', 'কৃদ', 'কা.সৰ্ব', 'বা.সৰ্ব', 'ব্য.সৰ্ব', 'বা,সৰ্ব',
             'ব্য,সৰ্ব', 'কা,সৰ্ব', 'স্হা', 'স্থা', 'অনুকা', 'সর্ব']
    return any(stem in s for stem in stems)


def is_assamese_only(line: str) -> bool:
    """Pure Assamese line of 1-4 words, no parens or POS."""
    line = line.strip().rstrip('}').rstrip(']').strip()
    if not line or '(' in line or ')' in line:
        return False
    if any(c.isascii() and c.isalpha() for c in line):
        return False
    words = line.split()
    if not (1 <= len(words) <= 4):
        return False
    return all(is_assamese(w, 0.7) for w in words)


def parse_dictionary(text: str) -> list[dict]:
    start = text.find('===== 201 =====')
    if start < 0:
        m = re.search(r'ব্ৰজাৱলী\s*[ভড]াষাৰ\s*অভিধান', text)
        start = m.start() if m else 0
    text = text[start:]

    raw_lines = []
    for line in text.split('\n'):
        ls = line.strip()
        if ls.startswith('====='):
            continue
        if re.search(r'ব্ৰজাৱলী\s*[ভড]াষাৰ\s*[অঅ]ভিধান', ls):
            continue
        if 'অভিধান' in ls and 'ব্ৰজাৱলী' in ls:
            continue
        if re.match(r'^\s*[০-৯\d]{1,4}\s*$', ls):
            continue
        if not is_assamese(ls, 0.15) and len(ls) <= 40:
            continue
        raw_lines.append(line.rstrip())

    pos_marker = re.compile(r'\(([^()]{1,30})\)')

    entries: list[dict] = []
    pending_heads: list[str] = []
    cur_chunk: list[str] = []  # body lines for the current entry
    cur_inline_head: str = ''

    def flush():
        nonlocal pending_heads, cur_chunk, cur_inline_head
        if cur_chunk:
            blob = ' '.join(s.strip() for s in cur_chunk).strip()
            blob = clean_text(blob)
            heads_blob = clean_text(cur_inline_head)
            entry = _build_entry(heads_blob, blob, pending_heads)
            if entry:
                entries.append(entry)
        pending_heads = []
        cur_chunk = []
        cur_inline_head = ''

    for line in raw_lines:
        ls = line.strip().lstrip('}]|').strip()

        # Check if this line opens a new entry: contains (POS) where the
        # text inside parens is a POS tag.
        opens = False
        head_in_line = ''
        body_in_line = ls
        for m in pos_marker.finditer(ls):
            inside = m.group(1).strip()
            if looks_like_pos(inside):
                # Heuristic: only the FIRST POS marker delimits the head
                head_in_line = ls[:m.start()].strip()
                body_in_line = ls[m.start():]
                opens = True
                break

        if opens:
            flush()
            cur_inline_head = head_in_line
            cur_chunk = [body_in_line]
            continue

        # Otherwise: orphan-Assamese-headword line OR continuation
        is_orphan_head = is_assamese_only(ls)
        if is_orphan_head and not cur_chunk:
            # leading head before any body
            pending_heads.append(ls.rstrip('}').rstrip(']').strip())
            continue
        if is_orphan_head and cur_chunk:
            # head for the *next* entry — flush current, queue this
            flush()
            pending_heads.append(ls.rstrip('}').rstrip(']').strip())
            continue

        # Continuation
        if cur_chunk:
            cur_chunk.append(ls)
        # else: drop

    flush()
    return entries


def _build_entry(inline_head: str, body: str, pending_heads: list[str]) -> dict | None:
    pos_re = re.compile(r'\(([^()]{1,30})\)')
    m = pos_re.search(body)
    if not m or not looks_like_pos(m.group(1)):
        return None
    pos_part = m.group(1).strip().rstrip('.,।')

    head_text = body[:m.start()].strip()
    inline_full = (inline_head + ' ' + head_text).strip()

    raw_heads = []
    for src in [*pending_heads, inline_full]:
        if not src:
            continue
        for piece in re.split(r'[,;]\s*', src):
            piece = piece.strip().rstrip('}').rstrip(']').strip()
            if piece and is_assamese(piece, 0.55):
                raw_heads.append(piece)
    if not raw_heads:
        return None

    rest = body[m.end():].strip()
    rest = clean_text(rest)
    cite_match = re.search(r'\(([^()]{2,400})\)\s*$', rest)
    if cite_match:
        gloss_part = rest[:cite_match.start()].strip()
        citation = clean_text(cite_match.group(1))
    else:
        gloss_part = rest
        citation = ''

    gloss_part = clean_text(gloss_part)
    if not gloss_part:
        return None
    glosses = []
    for piece in re.split(r'[,।]\s*', gloss_part):
        p = clean_text(piece)
        if p and is_assamese(p, 0.5):
            glosses.append(p)
    if not glosses:
        return None

    def uniq(xs):
        seen = set()
        out = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return {
        'brajawali': uniq(raw_heads),
        'pos': pos_part,
        'pos_normalised': POS_TAGS.get(pos_part, 'unknown'),
        'assamese': uniq(glosses),
        'citation': citation,
    }


def build_indexes(entries: list[dict]) -> dict:
    forward: dict[str, list[dict]] = {}
    inverted: dict[str, list[dict]] = {}
    for e in entries:
        for bw in e['brajawali']:
            forward.setdefault(bw, []).append(e)
        for asm in e['assamese']:
            inverted.setdefault(asm, []).append(e)
    return {'forward': forward, 'inverted': inverted, 'entries': entries}


if __name__ == '__main__':
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/brajawali/full.txt')
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('/Users/hdeka/.claude/skills/brajawali/data/dictionary.json')
    text = src.read_text(encoding='utf-8')
    entries = parse_dictionary(text)
    indexes = build_indexes(entries)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(indexes, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Parsed {len(entries)} entries → {out}')
    print(f'  Brajawali → Assamese index size: {len(indexes["forward"])}')
    print(f'  Assamese  → Brajawali index size: {len(indexes["inverted"])}')
