# Chat PDF - Ứng dụng RAG Hiện đại

Ứng dụng chat với PDF sử dụng mô hình **Retrieval-Augmented Generation (RAG)** chạy hoàn toàn local. Giao diện hiện đại dạng ChatGPT với hỗ trợ streaming, trích dẫn nguồn, và chế độ dark/light.

## Giới thiệu mô hình

### Kiến trúc RAG
Hệ thống sử dụng mô hình RAG (Retrieval-Augmented Generation) gồm các thành phần:

- **Embedding Model** (nomic-embed-text): Chuyển đổi text/câu hỏi thành vector embedding
- **Vector Database** (ChromaDB): Lưu trữ và tìm kiếm các embedding của documents
- **Retrieval & Re-ranking**:
  - BM25: Tìm kiếm keyword-based
  - Semantic Similarity: Tìm kiếm dựa trên ngữ nghĩa
  - Kết hợp 2 phương pháp (50-50) để lấy top-K đoạn văn phù hợp nhất
  - Re-order theo vị trí trong tài liệu gốc để đảm bảo thứ tự đọc tự nhiên
- **LLM** (Ollama hoặc Sambanova): Sinh câu trả lời dựa trên context được retrieve

### Quy trình hoạt động
1. **Upload PDF** → Chuyển thành Markdown → Chia nhỏ thành chunks
2. **Indexing** → Tạo embedding cho mỗi chunk → Lưu vào ChromaDB
3. **Query** → Tìm kiếm top-K chunks liên quan → Re-rank → Build context
4. **Generation** → Gửi context + câu hỏi tới LLM → Streaming response
5. **Citation** → Hiển thị các chunks đã dùng để trả lời

## Yêu cầu hệ thống

- Python 3.8+
- Ollama (để chạy embedding + LLM local)
- 4GB+ RAM khuyến nghị

## Cách chạy

### 1. Cài đặt Ollama
- Tải từ https://ollama.com/
- Pull các model cần thiết:
  ```bash
  ollama pull nomic-embed-text:latest  # Model embedding (bắt buộc)
  ollama pull qwen2.5:latest           # Model trả lời (hoặc model khác)
  ```

### 2. Cài đặt Python dependencies
```bash
pip install -r requirements.txt
python -m nltk.downloader punkt punkt_tab
```

### 3. Chạy ứng dụng
```bash
streamlit run app.py
```
Mở trình duyệt: `http://localhost:8501`

### Sử dụng LLM cloud (Sambanova)
- Copy `.env.example` thành `.env`
- Điền API key hoặc nhập trực tiếp ở sidebar

## Cấu trúc dự án

```
├── rag_core/              # Logic RAG chính
│   ├── rag.py            # Retrieval + re-ranking
│   ├── llm_inference.py  # Gọi Ollama/Sambanova
│   └── md_convertor.py   # Xử lý PDF
├── app_services/         # Services
│   └── ingest_service.py # Upload & indexing PDF
├── ui/                   # UI components
│   ├── components.py     # Chat UI, sidebar
│   └── theme.py          # Dark/light theme
├── app.py                # Entry point (Streamlit)
└── requirements.txt
```
