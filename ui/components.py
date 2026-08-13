import subprocess
import streamlit as st


def get_available_models():
    """Fetches installed Ollama models (unchanged logic from original app.py)."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        models = [
            line.split(" ")[0] for line in result.stdout.strip().split("\n")
            if line and "NAME" not in line and "embed" not in line.lower()
        ]
        return models, True
    except Exception:
        return [], False


def render_model_status(is_online: bool):
    dot_class = "online" if is_online else "offline"
    label = "Ollama đang chạy" if is_online else "Không kết nối được Ollama"
    st.markdown(
        f'<div class="status-pill"><span class="status-dot {dot_class}"></span>{label}</div>',
        unsafe_allow_html=True,
    )


def render_doc_chip(name: str, active: bool, key_prefix: str):
    active_class = "active" if active else ""
    col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
    with col1:
        st.markdown(f'<div class="doc-chip {active_class}">📄 {name}</div>', unsafe_allow_html=True)
    with col2:
        select_clicked = st.button("✅", key=f"{key_prefix}_select", help="Chọn tài liệu này")
    with col3:
        delete_clicked = st.button("🗑️", key=f"{key_prefix}_delete", help="Xoá tài liệu này")
    return select_clicked, delete_clicked


def render_citation_accordion(sources: list[str], source_filenames: list[str] = None):
    """Collapsible 'Nguồn trích dẫn' section shown under an assistant message."""
    if not sources:
        return
    with st.expander(f"📚 Nguồn trích dẫn ({len(sources)} đoạn)"):
        for i, chunk in enumerate(sources, start=1):
            label = f"Đoạn {i}"
            if source_filenames and i - 1 < len(source_filenames):
                label += f" — {source_filenames[i - 1]}"
            st.markdown(f"**{label}**")
            st.markdown(f'<div class="citation-block">{chunk}</div>', unsafe_allow_html=True)
