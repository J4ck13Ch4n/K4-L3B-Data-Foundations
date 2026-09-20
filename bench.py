"""Benchmark harness: chunk the Shopee return/refund/warranty corpus, load it
into EmbeddingStore, and run the 5 group benchmark queries.

Usage:
    .venv/bin/python bench.py

Change the STRATEGY constant below to switch chunking strategy — that is the
only line each team member should edit to compare their own configuration.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

DATA_DIR = Path("data/shopee-return-refund")
RESULT_FILE = Path("ket_qua_benchmark.txt")


def build_embedder():
    """Pick the embedding backend from .env, same provider logic as main.py.
    Falls back to MockEmbedder if the provider or its dependency/key is missing."""
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            return LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception as exc:
            print(f"[bench] local embedder unavailable ({exc}); falling back to mock")
            return _mock_embed
    if provider == "openai":
        try:
            return OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception as exc:
            print(f"[bench] openai embedder unavailable ({exc}); falling back to mock")
            return _mock_embed
    if provider == "gemini":
        try:
            return GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
        except Exception as exc:
            print(f"[bench] gemini embedder unavailable ({exc}); falling back to mock")
            return _mock_embed
    return _mock_embed

# --- one-line strategy switch: "fixed" | "sentence" | "recursive" | "heading" ---
STRATEGY = "sentence"

CHUNK_SIZE = 350
OVERLAP = 40
MAX_SENTENCES = 2


# ---------------------------------------------------------------------------
# Frontmatter parsing (no PyYAML in this venv — parse the simple key: value
# frontmatter used by every file in data/shopee-return-refund/ by hand).
# ---------------------------------------------------------------------------
def parse_frontmatter(raw_text: str) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---"):
        return {}, raw_text
    parts = raw_text.split("---", 2)
    if len(parts) < 3:
        return {}, raw_text
    _, fm_block, body = parts
    metadata: dict[str, str] = {}
    for line in fm_block.strip().splitlines():
        match = re.match(r"^(\w+):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        value = value.strip('"')
        metadata[key] = value
    return metadata, body.strip()


# ---------------------------------------------------------------------------
# Chunking strategy dispatch
# ---------------------------------------------------------------------------
def heading_chunks(body: str, title: str) -> list[str]:
    """Split by paragraph under the single H1, re-attaching the title to each
    piece so a chunk never loses the 'what section is this' context."""
    lines = body.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    text = "\n".join(lines).strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [f"{title}\n\n{p}" for p in paragraphs] if paragraphs else [title]


def chunk_body(body: str, title: str) -> list[str]:
    if STRATEGY == "fixed":
        return FixedSizeChunker(chunk_size=CHUNK_SIZE, overlap=OVERLAP).chunk(body)
    if STRATEGY == "sentence":
        return SentenceChunker(max_sentences_per_chunk=MAX_SENTENCES).chunk(body)
    if STRATEGY == "recursive":
        return RecursiveChunker(chunk_size=CHUNK_SIZE).chunk(body)
    if STRATEGY == "heading":
        return heading_chunks(body, title)
    raise ValueError(f"Unknown STRATEGY: {STRATEGY!r}")


def load_corpus() -> list[Document]:
    documents: list[Document] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(raw)
        title = frontmatter.get("title", path.stem)
        chunks = chunk_body(body, title)
        for i, chunk_text in enumerate(chunks):
            documents.append(
                Document(
                    id=f"{path.stem}#{i}",
                    content=chunk_text,
                    metadata={**frontmatter, "doc_id": path.stem, "chunk_index": i},
                )
            )
    return documents


# ---------------------------------------------------------------------------
# The 5 group benchmark queries (bilingual; the Vietnamese text is what is
# actually embedded/searched, since the corpus itself is in Vietnamese).
# `evidence` is a verbatim substring of the gold document's body text used
# for the second (content-level) grading tier, not just doc_id-in-top-3.
# ---------------------------------------------------------------------------
QUERIES: list[dict[str, Any]] = [
    {
        "id": "Q1",
        "query_en": "How long does a buyer have to request a return or refund?",
        "query_vi": "Người mua có bao lâu để gửi yêu cầu trả hàng hoặc hoàn tiền?",
        "filter": {"audience": "buyer"},
        "gold_doc": "buyer-return-eligibility-deadline",
        "evidence": "15 ngày",
    },
    {
        "id": "Q2",
        "query_en": "What must a seller do after a buyer opens a return request?",
        "query_vi": "Người bán phải làm gì sau khi người mua tạo yêu cầu trả hàng?",
        "filter": {"audience": "seller"},
        "gold_doc": "seller-refund-response-deadline",
        "evidence": "02 ngày lịch",
    },
    {
        "id": "Q3",
        "query_en": "When is the buyer's refund released after a return is approved?",
        "query_vi": "Khi nào người mua nhận được tiền hoàn sau khi yêu cầu trả hàng được chấp thuận?",
        "filter": {"audience": "buyer"},
        "gold_doc": "buyer-refund-processing-review",
        "evidence": "xác nhận đã nhận được sản phẩm hoàn trả",
    },
    {
        "id": "Q4",
        "query_en": "Which reasons and evidence can support a return or refund claim?",
        "query_vi": "Những lý do và bằng chứng nào có thể hỗ trợ yêu cầu trả hàng hoặc hoàn tiền?",
        "filter": None,
        "gold_doc": "buyer-return-reasons-refund-timeline",
        "evidence": "chưa mở hộp",
    },
    {
        "id": "Q5",
        "query_en": "Who pays return shipping and what should the seller do with the parcel?",
        "query_vi": "Ai trả phí vận chuyển hoàn trả và người bán cần làm gì với gói hàng?",
        "filter": {"audience": "seller"},
        "gold_doc": "seller-refund-response-deadline",
        "evidence": "xác nhận đã nhận được Sản Phẩm Hoàn Trả",
    },
]


def cached_embedder(embedder):
    """Wrap an embedder with a content-hash cache so re-running bench.py (or
    embedding the same chunk text more than once) does not re-spend API calls."""
    cache: dict[str, list[float]] = {}

    def call(text: str) -> list[float]:
        if text not in cache:
            cache[text] = embedder(text)
        return cache[text]

    return call


def score_query(results: list[dict[str, Any]], gold_doc: str, evidence: str) -> tuple[int, bool, bool]:
    context = "\n".join(r["content"] for r in results)
    doc_in_top3 = any(r["metadata"].get("doc_id") == gold_doc for r in results)
    evidence_present = evidence in context
    if results and results[0]["metadata"].get("doc_id") == gold_doc and evidence_present:
        score = 2
    elif doc_in_top3 and evidence_present:
        score = 1
    else:
        score = 0
    return score, doc_in_top3, evidence_present


def main() -> None:
    lines: list[str] = []

    def emit(text: str = "") -> None:
        print(text)
        lines.append(text)

    md_files = sorted(DATA_DIR.glob("*.md"))
    documents = load_corpus()
    embedder = build_embedder()
    backend_name = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    store = EmbeddingStore(embedding_fn=cached_embedder(embedder))
    store.add_documents(documents)

    emit(f"=== bench.py — strategy={STRATEGY} chunk_size={CHUNK_SIZE} overlap={OVERLAP} ===")
    emit(f"Documents: {len(md_files)} | Chunks loaded: {store.get_collection_size()}")
    emit(f"Embedding backend: {backend_name}")
    emit("")

    total_score = 0
    max_score = 0
    for q in QUERIES:
        emit(f"--- {q['id']} ---")
        emit(f"EN: {q['query_en']}")
        emit(f"VI: {q['query_vi']}")
        emit(f"filter: {q['filter']}")
        results = store.search_with_filter(q["query_vi"], top_k=3, metadata_filter=q["filter"])
        for rank, r in enumerate(results, start=1):
            preview = r["content"][:90].replace("\n", " ")
            emit(f"  [{rank}] score={r['score']:.4f} doc_id={r['metadata'].get('doc_id')} :: {preview}...")
        score, doc_hit, evidence_hit = score_query(results, q["gold_doc"], q["evidence"])
        total_score += score
        max_score += 2
        emit(
            f"  gold_doc={q['gold_doc']!r} doc_in_top3={doc_hit} "
            f"evidence_in_context={evidence_hit} -> score={score}/2"
        )
        emit("")

    emit(f"TOTAL SCORE: {total_score}/{max_score}")
    emit("")

    emit("=== A/B on every filtered query: with vs without metadata_filter ===")
    for q in QUERIES:
        if q["filter"] is None:
            continue
        emit(f"--- {q['id']} ({q['query_vi']}) ---")
        top3_by_label: dict[str, list[str]] = {}
        for label, flt in ((f"A) filter={q['filter']}", q["filter"]), ("B) no filter", None)):
            results = store.search_with_filter(q["query_vi"], top_k=3, metadata_filter=flt)
            doc_ids = [r["metadata"].get("doc_id") for r in results]
            top3_by_label[label] = doc_ids
            emit(f"  {label}")
            for rank, r in enumerate(results, start=1):
                emit(f"    [{rank}] score={r['score']:.4f} doc_id={r['metadata'].get('doc_id')}")
        changed = list(top3_by_label.values())[0] != list(top3_by_label.values())[1]
        emit(f"  => filter changed top-3: {changed}")
        emit("")

    RESULT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"(written to {RESULT_FILE})")


if __name__ == "__main__":
    main()
