import os
import re
import time
import streamlit as st

from rag_core.rag import RAGSystem
from app_services.ingest_service import index_pdf, list_indexed_documents, delete_document, DB_PATH
from app_services.history_service import (
    create_session, add_message, list_sessions, load_messages, delete_session,
)
from ui.theme import inject_theme_css
from ui.components import get_available_models, render_model_status, render_doc_chip, render_citation_accordion

st.set_page_config(page_title="Chat with PDF", page_icon="💬", layout="wide")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
defaults = {
    "dark_mode": False,
    "messages": [],
    "indexed_docs": None,       # list of collection_names, lazy-loaded
    "doc_labels": {},           # collection_name -> display filename
    "active_doc": None,         # currently selected collection_name
    "max_messages": 50,
    "current_session_id": None,   # id of the chat session being persisted
    "chat_sessions": None,        # cached list of past sessions, lazy-loaded
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.indexed_docs is None:
    st.session_state.indexed_docs = list_indexed_documents(DB_PATH)

if st.session_state.chat_sessions is None:
    st.session_state.chat_sessions = list_sessions()

inject_theme_css(dark=st.session_state.dark_mode)

def remove_think_tags(text: str) -> str:
    return re.sub(r"^.*?</think>", "", text, flags=re.DOTALL).strip()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    top_l, top_r = st.columns([0.7, 0.3])
    with top_l:
        st.markdown("### 💬 Chat with PDF")
    with top_r:
        st.session_state.dark_mode = st.toggle("🌙", value=st.session_state.dark_mode, label_visibility="collapsed")

    available_models, ollama_online = get_available_models()
    render_model_status(ollama_online)
    if not ollama_online:
        st.caption("Cài Ollama và chạy `ollama serve`, sau đó `ollama pull <model>`.")

    st.divider()

    # --- Upload (drag & drop is native to st.file_uploader) ---
    st.markdown("**📥 Tài liệu**")
    uploaded_files = st.file_uploader(
        "Kéo & thả PDF vào đây, hoặc bấm để chọn",
        type="pdf",
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    processing_mode = st.radio(
        "Chế độ xử lý", ["Simple Processing", "Advanced Processing"],
        help="Simple: trích xuất văn bản trực tiếp (nhanh). Advanced: OCR qua Marker, dùng cho PDF scan (chậm hơn).",
    )
    chunk_size = st.number_input("Chunk size", min_value=128, max_value=2560, value=512, step=128)

    if uploaded_files:
        for f in uploaded_files:
            already = any(st.session_state.doc_labels.get(c) == f.name for c in st.session_state.indexed_docs)
            if already:
                continue
            # Use Streamlit's internal unique file_id (not the filename) as the
            # widget key, so uploading two files with the same name never
            # collides (StreamlitDuplicateElementKey).
            if st.button(f"⚡ Xử lý: {f.name}", key=f"process_{f.file_id}"):
                with st.spinner(f"Đang xử lý {f.name}..."):
                    collection_name, n_chunks = index_pdf(
                        pdf_bytes=f.getbuffer(),
                        filename=f.name,
                        processing_mode=processing_mode,
                        chunk_size=chunk_size,
                        db_path=DB_PATH,
                    )
                st.session_state.indexed_docs = [c for c in st.session_state.indexed_docs if c != collection_name]
                st.session_state.indexed_docs.append(collection_name)
                st.session_state.doc_labels[collection_name] = f.name
                st.session_state.active_doc = collection_name
                st.success(f"Đã lập chỉ mục {f.name} ({n_chunks} đoạn).")
                st.rerun()

    # --- List of indexed PDFs ---
    if st.session_state.indexed_docs:
        st.caption("Tài liệu đã lập chỉ mục — chọn ✅ để hỏi-đáp, 🗑️ để xoá:")
        for c in list(st.session_state.indexed_docs):
            label = st.session_state.doc_labels.get(c, c)
            col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
            with col1:
                active = c == st.session_state.active_doc
                st.markdown(
                    f'<div class="doc-chip {"active" if active else ""}">📄 {label}</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("✅", key=f"sel_{c}", help="Chọn tài liệu này"):
                    st.session_state.active_doc = c
                    st.session_state.messages = []
                    st.session_state.current_session_id = None
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{c}", help="Xoá tài liệu này"):
                    delete_document(c, DB_PATH)
                    st.session_state.indexed_docs.remove(c)
                    st.session_state.doc_labels.pop(c, None)
                    if st.session_state.active_doc == c:
                        st.session_state.active_doc = None
                    st.rerun()
    else:
        st.caption("Chưa có tài liệu nào. Upload PDF ở trên để bắt đầu.")

    st.divider()

    # --- Params ---
    st.markdown("**⚙️ Cấu hình**")
    llm_provider = st.selectbox("Nhà cung cấp LLM", ["Ollama", "Sambanova"], index=0)
    if llm_provider == "Ollama":
        selected_model = st.selectbox("Model Ollama", available_models or ["(chưa có model)"], index=0)
        llm_name = None
        api_key = None
    else:
        selected_model = None
        llm_name = st.selectbox(
            "Model Sambanova",
            ["DeepSeek-R1-Distill-Llama-70B", "DeepSeek-V3-0324", "DeepSeek-R1", "Qwen3-32B", "QwQ-32B"],
            index=0,
        )
        api_key = st.text_input("Sambanova API Key", type="password", value=os.getenv("API_KEY", ""))

    n_results = st.slider("Top-K (số đoạn truy xuất)", min_value=1, max_value=15, value=5)
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.7, step=0.1)
    stream_enabled = st.toggle("Hiệu ứng gõ chữ (streaming)", value=True)

    st.divider()

    # --- Persistent chat history ---
    st.markdown("**🕘 Lịch sử trò chuyện**")
    if st.session_state.chat_sessions:
        for s in st.session_state.chat_sessions[:15]:
            doc_label = st.session_state.doc_labels.get(s["collection_name"], s["collection_name"])
            is_current = s["id"] == st.session_state.current_session_id
            col1, col2 = st.columns([0.82, 0.18])
            with col1:
                btn_label = f'{"🟢" if is_current else "💬"} {s["title"] or "(Không có tiêu đề)"}'
                if st.button(btn_label, key=f"hist_{s['id']}", use_container_width=True, help=f"Tài liệu: {doc_label}"):
                    st.session_state.messages = load_messages(s["id"])
                    st.session_state.current_session_id = s["id"]
                    st.session_state.active_doc = s["collection_name"]
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delhist_{s['id']}", help="Xoá cuộc trò chuyện này"):
                    delete_session(s["id"])
                    st.session_state.chat_sessions = list_sessions()
                    if st.session_state.current_session_id == s["id"]:
                        st.session_state.current_session_id = None
                        st.session_state.messages = []
                    st.rerun()
    else:
        st.caption("Chưa có cuộc trò chuyện nào được lưu.")

    st.divider()

    if st.button("🆕 Cuộc trò chuyện mới", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_session_id = None
        st.rerun()

# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------
if not st.session_state.active_doc:
    st.info("👈 Upload và chọn một tài liệu PDF ở thanh bên để bắt đầu trò chuyện.")
else:
    active_label = st.session_state.doc_labels.get(st.session_state.active_doc, st.session_state.active_doc)
    st.caption(f"Đang trò chuyện với: **{active_label}**")

for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            render_citation_accordion(msg["sources"], msg.get("source_filenames"))

if len(st.session_state.messages) >= st.session_state.max_messages:
    st.info("Đã đạt giới hạn số tin nhắn. Vui lòng bắt đầu cuộc trò chuyện mới.")
elif query := st.chat_input("Hỏi điều gì đó về tài liệu... (Enter để gửi, Shift+Enter xuống dòng)"):
    if not st.session_state.active_doc:
        st.error("Vui lòng chọn một tài liệu PDF đã lập chỉ mục trước.")
    else:
        if not st.session_state.current_session_id:
            title = query.strip()[:60]
            st.session_state.current_session_id = create_session(
                collection_name=st.session_state.active_doc, title=title
            )
            st.session_state.chat_sessions = list_sessions()

        st.session_state.messages.append({"role": "user", "content": query})
        add_message(st.session_state.current_session_id, "user", query)
        with st.chat_message("user", avatar="🧑"):
            st.markdown(query)

        with st.chat_message("assistant", avatar="🤖"):
            rag_system = RAGSystem(
                collection_name=st.session_state.active_doc, db_path=DB_PATH, n_results=n_results
            )
            try:
                if llm_provider == "Ollama":
                    if stream_enabled:
                        # Retrieve + rerank first (unchanged core logic), then stream the LLM answer.
                        chunks, embeddings, metadatas = rag_system._retrieve(query.strip(), n_results=20)
                        sources = rag_system._rerank_docs(chunks, embeddings, query.strip(), top_k=n_results, metadatas=metadatas) if chunks else []
                        context = "\n\n########\n\n".join(sources)
                        prompt = rag_system._get_prompt(query.strip(), context)

                        placeholder = st.empty()
                        full_text = ""
                        with st.spinner("Đang suy nghĩ..."):
                            for token in rag_system.llm_inference.generate_text_ollama_stream(
                                prompt=prompt, model_name=selected_model, temperature=temperature
                            ):
                                full_text += token
                                placeholder.markdown(remove_think_tags(full_text) + "▌")
                        placeholder.markdown(remove_think_tags(full_text))
                        response_text = remove_think_tags(full_text)
                    else:
                        with st.spinner("Đang suy nghĩ..."):
                            result = rag_system.generate_response(query.strip(), selected_model, temperature=temperature)
                        llm_response, resp_time, n, in_tok, out_tok, sources = result
                        response_text = remove_think_tags(llm_response)
                        st.markdown(response_text)
                        st.caption(f"⏱ {resp_time} · {selected_model} · {in_tok}→{out_tok} tokens")
                else:
                    with st.spinner("Đang suy nghĩ..."):
                        result = rag_system.generate_response2(query.strip(), llm_name, api_key=api_key, temperature=temperature)
                    llm_response, resp_time, n, in_tok, out_tok, sources = result
                    response_text = remove_think_tags(llm_response)
                    st.markdown(response_text)
                    st.caption(f"⏱ {resp_time} · {llm_name} · {in_tok}→{out_tok} tokens")

                source_filenames = [active_label] * len(sources) if sources else []
                render_citation_accordion(sources, source_filenames)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "sources": sources,
                    "source_filenames": source_filenames,
                })
                add_message(
                    st.session_state.current_session_id, "assistant", response_text,
                    sources=sources, source_filenames=source_filenames,
                )
                st.session_state.chat_sessions = list_sessions()
            except Exception as e:
                err = f"Lỗi: {e}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
                add_message(st.session_state.current_session_id, "assistant", err)