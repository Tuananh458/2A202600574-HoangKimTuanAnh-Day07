"""Benchmark retrieval over the group document set (Phase 2, Exercise 3.4).

Strategy under test: RecursiveChunker (chunk_size=300) + metadata filtering.
Each document is split into chunks; every chunk becomes one indexed record so
retrieval works at the chunk level (chunk-level RAG index).

Run:
    python benchmark.py

Uses the deterministic mock embedder by default, so results are reproducible
without any API key. Set EMBEDDING_PROVIDER=local (and install
sentence-transformers) to benchmark with real semantic embeddings.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.chunking import RecursiveChunker
from src.embeddings import LocalEmbedder, OpenAIEmbedder, _mock_embed
from src.models import Document
from src.store import EmbeddingStore

# --- Document set: VinUni policies; metadata schema (source, lang, category) ---
DOC_META = {
    "quy_che_hoc_thuat_cu_nhan": {"ext": ".md", "lang": "vi", "category": "hoc_thuat"},
    "chinh_sach_hoc_bong": {"ext": ".md", "lang": "vi", "category": "hoc_bong"},
    "quy_dinh_trung_thuc_hoc_thuat": {"ext": ".md", "lang": "vi", "category": "ky_luat"},
    "quy_trinh_khieu_nai_diem": {"ext": ".md", "lang": "vi", "category": "khieu_nai"},
    "quy_trinh_tam_nghi_thoi_hoc": {"ext": ".md", "lang": "vi", "category": "nghi_hoc"},
    "yeu_cau_tieng_anh": {"ext": ".md", "lang": "vi", "category": "ngoai_ngu"},
    "credit_transfer_guideline_en": {"ext": ".md", "lang": "en", "category": "tin_chi"},
}

# --- 5 benchmark queries; (query, metadata_filter, gold_source) ---
QUERIES = [
    ("Sinh viên cần GPA tối thiểu bao nhiêu để duy trì học bổng?", None, "chinh_sach_hoc_bong"),
    ("Hành vi đạo văn bị xử lý kỷ luật như thế nào?", None, "quy_dinh_trung_thuc_hoc_thuat"),
    ("Quy trình khiếu nại điểm cuối kỳ gồm những bước nào?", None, "quy_trinh_khieu_nai_diem"),
    ("Yêu cầu tiếng Anh đầu vào cho chương trình cử nhân là gì?", None, "yeu_cau_tieng_anh"),
    ("What are the rules for transferring external credits?", {"lang": "en"}, "credit_transfer_guideline_en"),
]


def pick_embedder():
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
    if provider == "local":
        try:
            return LocalEmbedder()
        except Exception:
            return _mock_embed
    if provider == "openai":
        try:
            return OpenAIEmbedder()
        except Exception:
            return _mock_embed
    return _mock_embed


def build_store(embedder) -> EmbeddingStore:
    store = EmbeddingStore(collection_name="benchmark", embedding_fn=embedder)
    chunker = RecursiveChunker(chunk_size=300)
    records: list[Document] = []
    for stem, meta in DOC_META.items():
        text = Path(f"data/{stem}{meta['ext']}").read_text(encoding="utf-8")
        for i, chunk in enumerate(chunker.chunk(text)):
            records.append(
                Document(
                    id=f"{stem}__chunk_{i}",
                    content=chunk,
                    metadata={"source": stem, "lang": meta["lang"], "category": meta["category"]},
                )
            )
    store.add_documents(records)
    return store


def main() -> int:
    embedder = pick_embedder()
    backend = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    store = build_store(embedder)

    print(f"Embedding backend : {backend}")
    print(f"Indexed chunks    : {store.get_collection_size()}")
    print("=" * 78)

    relevant_in_top3 = 0
    for i, (query, flt, gold) in enumerate(QUERIES, start=1):
        if flt:
            results = store.search_with_filter(query, top_k=3, metadata_filter=flt)
        else:
            results = store.search(query, top_k=3)

        top_sources = [r["metadata"]["source"] for r in results]
        hit = gold in top_sources
        relevant_in_top3 += int(hit)

        top1 = results[0]
        preview = top1["content"][:90].replace("\n", " ")
        print(f"\nQ{i}: {query}")
        print(f"   filter={flt} gold={gold}")
        print(f"   top1: source={top1['metadata']['source']} score={top1['score']:.4f}")
        print(f"   top1 preview: {preview}...")
        print(f"   top3 sources: {top_sources}  relevant_in_top3={hit}")

    print("\n" + "=" * 78)
    print(f"Relevant in top-3: {relevant_in_top3} / {len(QUERIES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
