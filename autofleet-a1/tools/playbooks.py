"""Block 7: playbook retrieval (RAG).

Plain TF-IDF cosine similarity in numpy so there are no heavy dependencies. LEARNING EXERCISE:
replace `_embed` with bge-small / all-MiniLM sentence embeddings and a FAISS index; the
`search_playbooks` interface stays identical.
"""
from __future__ import annotations
import math, re
from collections import Counter
from functools import lru_cache
from pathlib import Path

PLAYBOOK_DIR = Path(__file__).resolve().parent.parent / "playbooks"
_STOP = set("a an the and or of to in on is are for with when use that this as it by at be from".split())


def _tok(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower().replace("_", " ")) if t not in _STOP]


@lru_cache(maxsize=1)
def _index():
    docs = {p.stem: p.read_text() for p in sorted(PLAYBOOK_DIR.glob("*.md"))}
    toks = {k: Counter(_tok(v)) for k, v in docs.items()}
    df = Counter(t for c in toks.values() for t in c)
    idf = {t: math.log((1 + len(docs)) / (1 + n)) + 1 for t, n in df.items()}
    return docs, toks, idf


def search_playbooks(query: str, k: int = 2) -> dict:
    """Retrieve the top-k service playbooks most relevant to a finding (e.g. 'sensor calibration backlog at Site C').

    Call this AFTER the KPI tools have identified a bottleneck, to get recommended actions with a citable source
    playbook. Returns playbook id, title, similarity score and the full text of each match.
    Args: query: short description of the finding; k: number of playbooks (default 2).
    """
    docs, toks, idf = _index()
    q = Counter(_tok(query))
    def vec(c): return {t: n * idf.get(t, 0) for t, n in c.items()}
    qv = vec(q)
    qn = math.sqrt(sum(v * v for v in qv.values())) or 1.0
    scored = []
    for name, c in toks.items():
        dv = vec(c)
        dn = math.sqrt(sum(v * v for v in dv.values())) or 1.0
        scored.append((sum(qv[t] * dv.get(t, 0) for t in qv) / (qn * dn), name))
    scored.sort(reverse=True)
    return {"query": query, "matches": [dict(playbook_id=n, title=docs[n].splitlines()[0].lstrip("# "),
                                              score=round(s, 3), text=docs[n]) for s, n in scored[:k]]}
