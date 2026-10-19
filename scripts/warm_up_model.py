"""Download the embedding model once, so the first real question is fast."""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

if __name__ == "__main__":
    model = SentenceTransformer(MODEL_NAME)
    model.encode(["warm up", "تجربة"])
    print(f"Embedding model ready: {MODEL_NAME}")
