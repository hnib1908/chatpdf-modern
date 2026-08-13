# Chat with PDF — Modern UI 

Giao diện SaaS hiện đại (kiểu ChatGPT/Claude/Perplexity) cho ứng dụng RAG chat-với-PDF chạy hoàn toàn local qua **Ollama**. Toàn bộ logic backend (đọc PDF, chunking, embedding, ChromaDB, retrieval + BM25/semantic re-ranking, gọi LLM) được **giữ nguyên** từ repo gốc — xem ghi chú ở đầu mỗi file trong `core/` để biết chính xác thay đổi gì (rất ít, chỉ mang tính bổ sung).

## Cấu trúc dự án

```
chatpdf-modern/
├── rag_core/               # Logic RAG gốc — không đổi thuật toán (đổi tên từ "core" để tránh trùng tên package)
│   ├── rag.py
│   ├── llm_inference.py
│   └── md_convertor.py
├── app_services/
│   └── ingest_service.py  # Ingest PDF (tách từ app.py gốc), hỗ trợ nhiều PDF (đổi tên từ "services" để tránh trùng tên package)
├── ui/
│   ├── theme.py           # CSS light/dark mode
│   └── components.py      # Sidebar, chat bubble, citation accordion
├── app.py                 # Điểm khởi chạy Streamlit (UI mới)
├── requirements.txt
└── .env.example
```

## Chạy ứng dụng (3 bước)

1. **Cài đặt Ollama và pull model** (bắt buộc — chạy hoàn toàn local):
   ```bash
   # Cài Ollama: https://ollama.com/
   ollama pull nomic-embed-text:latest   # model embedding, bắt buộc
   ollama pull qwen2.5:latest            # hoặc model bạn muốn dùng để trả lời
   ```

2. **Cài thư viện Python và dữ liệu NLTK**:
   ```bash
   pip install -r requirements.txt
   python -m nltk.downloader punkt punkt_tab
   ```

3. **Chạy ứng dụng**:
   ```bash
   streamlit run app.py
   ```
   Mở trình duyệt tại `http://localhost:8501`.

> Muốn dùng Sambanova (cloud) thay vì Ollama? Copy `.env.example` thành `.env` và điền `API_KEY`, hoặc nhập trực tiếp API key ở sidebar.



## Tính năng UI/UX

- **Sidebar**: trạng thái Ollama (● xanh/đỏ), upload PDF kéo-thả (đa tệp), danh sách PDF đã lập chỉ mục kèm nút chọn ✅ / xoá 🗑️, cấu hình nhanh (model, chunk size, top-K, temperature), nút "Cuộc trò chuyện mới".
- **Khung chat**: bong bóng user/assistant có avatar, `st.chat_input` hỗ trợ Enter gửi / Shift+Enter xuống dòng theo mặc định của Streamlit.
- **Streaming**: bật/tắt hiệu ứng gõ chữ (chỉ áp dụng khi dùng Ollama).
- **Citation Accordion**: mỗi câu trả lời có mục "📚 Nguồn trích dẫn" thu gọn/mở rộng, hiển thị đúng các đoạn văn bản đã dùng để trả lời (không có số trang cụ thể — repo gốc không tách text theo trang; nếu cần, có thể bật `page_chunks=True` trong `pymupdf4llm.to_markdown` ở bước ingest).
- **Dark/Light mode**: toggle 🌙 ở đầu sidebar.

## Giới hạn hiện tại

- Streaming typewriter chỉ hoạt động với nhà cung cấp **Ollama** (Sambanova trả kết quả một cục, giữ nguyên hành vi gốc).
- Chọn "tài liệu đang hỏi-đáp" là chọn 1 PDF tại 1 thời điểm (không truy vấn đồng thời nhiều PDF) — có thể mở rộng thêm nếu cần.
