"""VinUni Policy RAG — giao diện test trực quan.

Chạy:
    pip install streamlit
    streamlit run app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from benchmark import DOC_META, QUERIES, build_store, pick_embedder
from main import SAMPLE_FILES, demo_llm, load_documents_from_files
from src.agent import KnowledgeBaseAgent
from src.chunking import ChunkingStrategyComparator, compute_similarity
from src.embeddings import _mock_embed

load_dotenv(override=False)

st.set_page_config(
    page_title="VinUni Policy RAG Tester",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

CATEGORIES = sorted({meta["category"] for meta in DOC_META.values()})
LANGS = sorted({meta["lang"] for meta in DOC_META.values()})


def _set_provider(provider: str) -> None:
    os.environ["EMBEDDING_PROVIDER"] = provider


@st.cache_resource(show_spinner="Đang index chunk từ tài liệu VinUni...")
def get_chunk_store(provider: str):
    _set_provider(provider)
    embedder = pick_embedder()
    store = build_store(embedder)
    backend = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    return store, backend


@st.cache_resource(show_spinner="Đang load tài liệu gốc...")
def get_doc_store(provider: str):
    _set_provider(provider)
    embedder = pick_embedder()
    docs = load_documents_from_files(SAMPLE_FILES)
    from src.store import EmbeddingStore

    store = EmbeddingStore(collection_name="doc_level", embedding_fn=embedder)
    store.add_documents(docs)
    backend = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    return store, backend, docs


def _combined_corpus() -> str:
    parts: list[str] = []
    for stem, meta in DOC_META.items():
        path = Path(f"data/{stem}{meta['ext']}")
        parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def _render_result_card(rank: int, result: dict, highlight_gold: str | None = None) -> None:
    source = result["metadata"].get("source", "?")
    score = result["score"]
    lang = result["metadata"].get("lang", "")
    category = result["metadata"].get("category", "")
    is_gold = highlight_gold and source == highlight_gold
    border = "#2e7d32" if is_gold else "#e0e0e0"
    st.markdown(
        f"""
        <div style="border-left:4px solid {border};padding:0.75rem 1rem;margin-bottom:0.5rem;
                    background:#fafafa;border-radius:4px;">
            <strong>#{rank}</strong> &nbsp; score <code>{score:.4f}</code> &nbsp;
            source <code>{source}</code> &nbsp;
            <span style="color:#666;">lang={lang} · category={category}</span>
            {" &nbsp; <b style='color:#2e7d32;'>✓ GOLD</b>" if is_gold else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.text(result["content"][:500] + ("…" if len(result["content"]) > 500 else ""))


# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Cấu hình")
    provider = st.selectbox(
        "Embedding backend",
        options=["mock", "local", "openai"],
        index=["mock", "local", "openai"].index(
            os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
            if os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower() in ("mock", "local", "openai")
            else "mock"
        ),
        help="mock = mặc định lab (không cần API). local cần sentence-transformers.",
    )
    index_mode = st.radio(
        "Chế độ index",
        options=["chunk", "document"],
        format_func=lambda x: "Chunk-level (benchmark)" if x == "chunk" else "Document-level (main.py)",
    )
    top_k = st.slider("Top-K", min_value=1, max_value=10, value=3)

    if st.button("🔄 Xóa cache & reload index", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()

    st.divider()
    st.caption("Chủ đề: Chính sách & Quy định VinUni")
    st.caption(f"Tài liệu: {len(DOC_META)} file · Benchmark: {len(QUERIES)} query")

if index_mode == "chunk":
    store, backend = get_chunk_store(provider)
    doc_count = len(DOC_META)
    unit = "chunk"
else:
    store, backend, docs = get_doc_store(provider)
    doc_count = len(docs)
    unit = "document"

# --- Header ---
st.title("📋 VinUni Policy RAG Tester")
st.markdown(
    f"Backend: **{backend}** · Index: **{store.get_collection_size()}** {unit} "
    f"từ **{doc_count}** tài liệu"
)

tab_search, tab_bench, tab_chunk, tab_agent, tab_sim = st.tabs(
    ["🔍 Tìm kiếm", "📊 Benchmark", "✂️ Chunking", "🤖 Agent RAG", "📐 Similarity"]
)

# --- Tab: Search ---
with tab_search:
    st.subheader("Semantic Search")
    query = st.text_input(
        "Câu hỏi / query",
        placeholder="VD: Sinh viên cần GPA tối thiểu bao nhiêu để duy trì học bổng?",
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_lang = st.selectbox("Lọc lang", ["(tất cả)"] + LANGS)
    with col2:
        filter_cat = st.selectbox("Lọc category", ["(tất cả)"] + CATEGORIES)
    with col3:
        use_filter = st.checkbox("Bật metadata filter", value=False)

    if st.button("Tìm kiếm", type="primary", disabled=not query.strip()):
        metadata_filter: dict[str, str] = {}
        if use_filter:
            if filter_lang != "(tất cả)":
                metadata_filter["lang"] = filter_lang
            if filter_cat != "(tất cả)":
                metadata_filter["category"] = filter_cat

        if metadata_filter:
            results = store.search_with_filter(query, top_k=top_k, metadata_filter=metadata_filter)
            st.info(f"Filter: `{metadata_filter}`")
        else:
            results = store.search(query, top_k=top_k)

        if not results:
            st.warning("Không có kết quả.")
        else:
            for i, r in enumerate(results, start=1):
                _render_result_card(i, r)

# --- Tab: Benchmark ---
with tab_bench:
    st.subheader("5 Benchmark Queries (nhóm thống nhất)")
    if st.button("▶ Chạy toàn bộ benchmark", type="primary"):
        rows = []
        relevant = 0
        for i, (q, flt, gold) in enumerate(QUERIES, start=1):
            if flt:
                results = store.search_with_filter(q, top_k=3, metadata_filter=flt)
            else:
                results = store.search(q, top_k=3)
            top_sources = [r["metadata"]["source"] for r in results]
            hit = gold in top_sources
            relevant += int(hit)
            top1 = results[0] if results else None
            rows.append(
                {
                    "#": i,
                    "Query": q[:60] + ("…" if len(q) > 60 else ""),
                    "Gold": gold,
                    "Top-1": top1["metadata"]["source"] if top1 else "—",
                    "Score": f"{top1['score']:.4f}" if top1 else "—",
                    "Top-1 đúng": "✓" if top1 and top1["metadata"]["source"] == gold else "✗",
                    "Gold trong top-3": "✓" if hit else "✗",
                }
            )

        st.metric("Relevant in top-3", f"{relevant} / {len(QUERIES)}")
        st.dataframe(rows, use_container_width=True, hide_index=True)

        for i, (q, flt, gold) in enumerate(QUERIES, start=1):
            with st.expander(f"Q{i}: {q}"):
                if flt:
                    results = store.search_with_filter(q, top_k=3, metadata_filter=flt)
                    st.caption(f"Filter: `{flt}` · Gold: `{gold}`")
                else:
                    results = store.search(q, top_k=3)
                    st.caption(f"Gold: `{gold}`")
                for j, r in enumerate(results, start=1):
                    _render_result_card(j, r, highlight_gold=gold)

# --- Tab: Chunking ---
with tab_chunk:
    st.subheader("So sánh 3 chiến lược chunking")
    chunk_size = st.number_input("chunk_size", min_value=100, max_value=1000, value=300, step=50)
    if st.button("So sánh", type="primary"):
        text = _combined_corpus()
        res = ChunkingStrategyComparator().compare(text, chunk_size=chunk_size)
        cols = st.columns(3)
        for col, (name, stats) in zip(cols, res.items()):
            with col:
                st.markdown(f"**{name}**")
                st.metric("Số chunk", stats["count"])
                st.metric("Độ dài TB", f"{stats['avg_length']:.1f}")
        strategy = st.selectbox("Xem preview chunk", list(res.keys()))
        preview_n = st.slider("Số chunk preview", 1, min(10, res[strategy]["count"]), 3)
        for i, chunk in enumerate(res[strategy]["chunks"][:preview_n], start=1):
            st.text_area(f"Chunk {i} ({len(chunk)} ký tự)", chunk, height=120)

# --- Tab: Agent ---
with tab_agent:
    st.subheader("KnowledgeBaseAgent (RAG)")
    question = st.text_area(
        "Câu hỏi",
        placeholder="VD: Quy trình khiếu nại điểm cuối kỳ gồm những bước nào?",
        height=80,
    )
    if st.button("Hỏi Agent", type="primary", disabled=not question.strip()):
        agent = KnowledgeBaseAgent(store=store, llm_fn=demo_llm)
        results = store.search(question, top_k=top_k)
        st.markdown("**Nguồn được retrieve:**")
        for i, r in enumerate(results, start=1):
            _render_result_card(i, r)
        st.markdown("**Câu trả lời Agent (demo LLM):**")
        answer = agent.answer(question, top_k=top_k)
        st.success(answer)

# --- Tab: Similarity ---
with tab_sim:
    st.subheader("Cosine Similarity (mock embedder)")
    st.caption("Dùng để thử nghiệm Ex 1.1 — so sánh dự đoán vs điểm thực tế.")
    col_a, col_b = st.columns(2)
    with col_a:
        sent_a = st.text_area("Câu A", "Sinh viên cần GPA 3.0 để duy trì học bổng.", height=80)
    with col_b:
        sent_b = st.text_area("Câu B", "Học bổng yêu cầu điểm trung bình tích lũy tối thiểu 3.0.", height=80)
    if st.button("Tính similarity", type="primary"):
        vec_a = _mock_embed(sent_a)
        vec_b = _mock_embed(sent_b)
        score = compute_similarity(vec_a, vec_b)
        st.metric("Cosine similarity", f"{score:.4f}")
        if score > 0.5:
            st.success("High similarity (theo ngưỡng > 0.5)")
        elif score < 0.1:
            st.info("Low similarity (theo ngưỡng < 0.1)")
        else:
            st.warning("Mid-range — mock embedder thường không phản ánh nghĩa thật")
