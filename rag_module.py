# rag_module.py ( to be replaced by claude thing )

import os
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Read medical info
with open("data/medical_docs.txt", "r") as f:
    docs = f.readlines()

# Clean and embed
texts = [d.strip() for d in docs if d.strip()]
embeddings = model.encode(texts)

# Build FAISS index
dimension = embeddings[0].shape[0]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings))

# Map index positions to texts
id_to_text = {i: text for i, text in enumerate(texts)}

# Main retrieval function
def retrieve_context(query, top_k=1):
    query_embedding = model.encode([query])
    D, I = index.search(np.array(query_embedding), top_k)
    results = [id_to_text[i] for i in I[0]]
    return "\n".join(results)
