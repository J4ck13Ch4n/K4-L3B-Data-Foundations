from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self._store = store
        self._llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        chunks = self._store.search(question, top_k=top_k)

        if not chunks:
            return (
                "Không tìm thấy thông tin liên quan trong knowledge base để trả lời câu hỏi này."
            )

        context_lines = []
        for i, chunk in enumerate(chunks, start=1):
            source = chunk.get("metadata", {}).get("doc_id", "unknown")
            context_lines.append(f"[{i}] (source: {source}) {chunk['content']}")
        context = "\n\n".join(context_lines)

        prompt = (
            "You are a helpful assistant answering questions using only the "
            "numbered context passages below. Cite the passage numbers you "
            "relied on (e.g. [1], [2]) in your answer. If the context does "
            "not contain the answer, say so explicitly instead of guessing "
            "or using outside knowledge.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )
        return self._llm_fn(prompt)
