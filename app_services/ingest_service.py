# services/ingest_service.py
#
# NOTE FOR REVIEWERS:
# This is the SAME ingest logic that lived inline inside the original app.py
# (Simple Processing via pymupdf4llm, Advanced Processing via Marker OCR,
# RecursiveCharacterTextSplitter with the same chunk_overlap=100, and
# Chroma.from_documents with the same OllamaEmbeddings model). Nothing about
# HOW a PDF is read, split or embedded was changed.
#
# What's new here (app-layer, not RAG-layer):
#   - Each uploaded PDF gets its own Chroma collection (named after the file)
#     instead of a single fixed "pdf_content" collection, so the sidebar can
#     list / switch between / delete multiple PDFs.
#   - Each chunk gets a small metadata dict {"source": filename} attached,
#     purely so the UI can label citations with the file they came from.

import os
import re
import shutil
import hashlib

import pymupdf4llm
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

from langchain_ollama import OllamaEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

# LangChain reorganized these two across versions:
#   old:  langchain.text_splitter.RecursiveCharacterTextSplitter / langchain.schema.Document
#   new:  langchain_text_splitters.RecursiveCharacterTextSplitter / langchain_core.documents.Document
# Try the new locations first, fall back to the old ones, so this works
# regardless of which LangChain version is installed.
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document

from rag_core.md_convertor import Convert2Markdown

TMP_DIR = "./tmp"
DB_PATH = "PDF_ChromaDB"


def sanitize_collection_name(filename: str) -> str:
    """Turns a filename into a safe, stable Chroma collection name."""
    base = os.path.splitext(filename)[0]
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", base).strip("_") or "doc"
    short_hash = hashlib.md5(filename.encode()).hexdigest()[:6]
    name = f"pdf_{slug}_{short_hash}"[:63]  # Chroma collection name length limit
    return name


def index_pdf(pdf_bytes: bytes, filename: str, processing_mode: str, chunk_size: int,
               db_path: str = DB_PATH, embedding_model: str = "nomic-embed-text:latest"):
    """
    Same pipeline as the original app.py inline block:
    save file -> extract text (Simple/Advanced) -> split into chunks -> embed -> store in Chroma.
    Returns (collection_name, num_chunks).
    """
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR, exist_ok=True)

    pdf_path = os.path.join(TMP_DIR, filename)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    if processing_mode == "Simple Processing":
        text = pymupdf4llm.to_markdown(pdf_path)
    elif processing_mode == "Advanced Processing":
        artifact_dict = create_model_dict()
        converter = PdfConverter(artifact_dict=artifact_dict)
        convert2md = Convert2Markdown()
        convert2md.pdf_to_markdown(marker_converter=converter, input_pdf=pdf_path, output_directory=TMP_DIR)
        markdown_path = os.path.join(TMP_DIR, f"{os.path.splitext(filename)[0]}.md")
        text = convert2md._load_file(markdown_path)
    else:
        raise ValueError(f"Unknown processing_mode: {processing_mode}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=100)
    chunks = text_splitter.split_text(text)

    # chunk_index records each chunk's original position in the document, so
    # retrieved chunks can later be re-ordered back into reading order instead
    # of being left in relevance-score order (which reads as jumbled excerpts).
    documents = [
        Document(page_content=chunk, metadata={"source": filename, "chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]

    collection_name = sanitize_collection_name(filename)

    Chroma.from_documents(
        documents=documents,
        embedding=OllamaEmbeddings(model=embedding_model),
        collection_name=collection_name,
        persist_directory=db_path,
    )

    return collection_name, len(chunks)


def list_indexed_documents(db_path: str = DB_PATH):
    """Lists PDFs already indexed in ChromaDB (persists across app restarts)."""
    import chromadb
    if not os.path.exists(db_path):
        return []
    client = chromadb.PersistentClient(path=db_path)
    collections = client.list_collections()
    return [c.name for c in collections if c.name.startswith("pdf_")]


def delete_document(collection_name: str, db_path: str = DB_PATH):
    """Deletes one PDF's collection from ChromaDB."""
    import chromadb
    client = chromadb.PersistentClient(path=db_path)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
