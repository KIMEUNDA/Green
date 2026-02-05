import os
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from PyPDF2 import PdfReader

load_dotenv()

CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')
COLLECTION_NAME = 'documents'

def get_chroma_client():
    """ChromaDB 클라이언트 반환 (로컬 폴더에 저장)"""
    client = chromadb.Client(Settings(
        is_persistent=True,
        persist_directory=CHROMA_DB_PATH,
        anonymized_telemetry=False
    ))
    return client

def get_collection():
    """컬렉션 반환 (없으면 생성)"""
    client = get_chroma_client()
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return collection, client

def extract_text_from_pdf(uploaded_file) -> str:
    """PDF 파일에서 텍스트 추출"""
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """텍스트를 청크로 분할 (중복 포함)"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def add_document(file_name: str, file_content: str):
    """문서를 ChromaDB에 저장"""
    collection, client = get_collection()

    # 기존 같은 파일명 문서 삭제
    existing = collection.get(where={"source": file_name})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    # 청크로 분할하여 저장
    chunks = chunk_text(file_content)
    ids = [f"{file_name}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": file_name, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    return len(chunks)

def query_documents(query: str, n_results: int = 3) -> list[dict]:
    """질문에 관련된 문서 청크 검색"""
    collection, _ = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    if not results["documents"] or not results["documents"][0]:
        return []

    docs = []
    for i, doc in enumerate(results["documents"][0]):
        docs.append({
            "text": doc,
            "source": results["metadatas"][0][i]["source"],
            "chunk_index": results["metadatas"][0][i]["chunk_index"]
        })
    return docs

def get_all_sources() -> list[str]:
    """저장된 문서 파일명 목록 반환"""
    collection, _ = get_collection()
    all_data = collection.get()
    if not all_data["metadatas"]:
        return []
    sources = list(set(m["source"] for m in all_data["metadatas"]))
    return sorted(sources)

def delete_document(file_name: str):
    """특정 파일명의 문서 삭제"""
    collection, client = get_collection()
    existing = collection.get(where={"source": file_name})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        return True
    return False
