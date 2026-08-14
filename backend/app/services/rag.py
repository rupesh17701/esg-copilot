"""Minimal, dependency-light retrieval over a report's text chunks.

Uses TF-IDF cosine similarity (scikit-learn) rather than embeddings — this
needs no API key and no network call, so retrieval works identically whether
or not an LLM is configured. It's the "R" in this app's RAG: the LLM client
(or the offline fallback) only ever sees the chunks this module selects.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def retrieve_relevant_chunks(chunks: list[str], query: str, top_k: int = 4) -> list[tuple[int, str, float]]:
    """Returns up to top_k (index, chunk_text, similarity_score) tuples, best first."""
    if not chunks:
        return []
    if len(chunks) == 1:
        return [(0, chunks[0], 1.0)]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    try:
        matrix = vectorizer.fit_transform(chunks + [query])
    except ValueError:
        # Vocabulary is empty (e.g. all-stopword chunks) — fall back to the
        # first few chunks rather than failing the request.
        return [(i, c, 0.0) for i, c in enumerate(chunks[:top_k])]

    query_vec = matrix[-1]
    chunk_vecs = matrix[:-1]
    scores = cosine_similarity(query_vec, chunk_vecs).flatten()

    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [(idx, chunks[idx], float(score)) for idx, score in ranked]
