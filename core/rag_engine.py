from transformers import pipeline
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load QA and embedding models (lightweight)
qa_model = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

class RAGStore:
    """Offline retrieval + Q&A memory."""
    def __init__(self):
        self.index = faiss.IndexFlatL2(384)
        self.chunks = []

    def build(self, text: str):
        """Split and store embeddings."""
        self.chunks = [text[i:i+500] for i in range(0, len(text), 500)]
        if not self.chunks:
            raise RuntimeError("No text chunks created.")
        embeddings = embed_model.encode(self.chunks)
        self.index.add(np.array(embeddings).astype("float32"))

    def query(self, question: str) -> str:
        """Find relevant chunks and answer locally."""
        if not self.chunks:
            return "No content loaded yet."
        q_emb = embed_model.encode([question]).astype("float32")
        D, I = self.index.search(q_emb, k=3)
        context = " ".join(self.chunks[i] for i in I[0])
        result = qa_model(question=question, context=context)
        return result.get("answer", "No answer found.")
