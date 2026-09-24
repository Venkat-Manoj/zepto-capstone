from __future__ import annotations

from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
DB = ROOT / "chroma_db"
COLLECTION_NAME = "zepto_policy"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def chunk_documents() -> tuple[list[str], list[str], list[dict]]:
    ids, texts, metadata = [], [], []
    for path in sorted(DOCS.glob("doc_*.txt")):
        text = path.read_text(encoding="utf-8").strip()
        # One chunk per document is sufficient for the short policy documents.
        ids.append(path.stem)
        texts.append(text)
        metadata.append({"document_id": path.stem, "source": path.name})
    if len(ids) != 8:
        raise RuntimeError(f"Expected 8 policy documents, found {len(ids)}")
    return ids, texts, metadata


def main() -> None:
    ids, texts, metadata = chunk_documents()
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()
    client = chromadb.PersistentClient(path=str(DB))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(ids=ids, documents=texts, metadatas=metadata, embeddings=embeddings)
    print(f"Embedded and stored {collection.count()} chunks in {COLLECTION_NAME}.")


if __name__ == "__main__":
    main()
