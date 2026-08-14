"""Pluggable LLM layer.

``AnthropicLLMClient`` calls Claude for narrative ESG summaries and chat
answers. ``OfflineLLMClient`` is a deterministic, template-based fallback
with the same interface, so the rest of the app (routes, RAG, scoring) never
needs to know or care whether a real API key is configured. Swap providers
by setting ``ANTHROPIC_API_KEY`` — no other code changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.config import Settings, get_settings

SYSTEM_PROMPT = """You are ESG Copilot, an assistant specialized in BRSR \
(Business Responsibility and Sustainability Report) analysis, ESG risk \
assessment, and carbon intelligence for Indian listed companies.

You are given retrieved excerpts from a specific company's BRSR filing, plus \
structured metrics already computed by a deterministic pipeline (ESG scores, \
carbon intensity, disclosure completeness). Answer questions grounded only in \
this context. If the context does not contain the answer, say so plainly \
rather than guessing. Keep answers concise and cite the specific figures or \
excerpts you rely on."""


@dataclass
class ChatTurn:
    role: str
    content: str


class LLMClient(ABC):
    source: str

    @abstractmethod
    def generate_summary(self, context: str) -> str: ...

    @abstractmethod
    def chat(self, context: str, history: list[ChatTurn], question: str) -> str: ...


class AnthropicLLMClient(LLMClient):
    source = "anthropic"

    def __init__(self, settings: Settings):
        import anthropic

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    def generate_summary(self, context: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Using the following structured ESG/carbon data and report "
                        "excerpts, write a concise (150-250 word) ESG risk narrative "
                        "summary for a sustainability analyst. Highlight the strongest "
                        "and weakest areas, and one or two concrete recommendations.\n\n"
                        f"{context}"
                    ),
                }
            ],
        )
        return _extract_text(response)

    def chat(self, context: str, history: list[ChatTurn], question: str) -> str:
        messages = [{"role": t.role, "content": t.content} for t in history]
        messages.append(
            {
                "role": "user",
                "content": f"Context from the BRSR report:\n\n{context}\n\nQuestion: {question}",
            }
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return _extract_text(response)


def _extract_text(response) -> str:
    parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    return "\n".join(parts).strip() or "(no response text returned)"


class OfflineLLMClient(LLMClient):
    """Deterministic fallback used when no ANTHROPIC_API_KEY is configured.

    Produces extractive, templated output from the same context an LLM would
    receive, so the app is fully functional (if less fluent) without any
    external API access.
    """

    source = "offline"

    def generate_summary(self, context: str) -> str:
        lines = [ln.strip() for ln in context.split("\n") if ln.strip()]
        highlights = lines[:8]
        return (
            "Offline mode summary (no LLM API key configured — this is a templated "
            "extract of the computed metrics, not a generated narrative):\n\n"
            + "\n".join(f"- {line}" for line in highlights)
            + "\n\nAdd an ANTHROPIC_API_KEY to unlock a fully AI-generated narrative "
            "summary with tailored recommendations."
        )

    def chat(self, context: str, history: list[ChatTurn], question: str) -> str:
        # The context is "<metrics summary>\n\nRelevant report excerpts:\n\n<excerpts>".
        # The excerpts are what actually answers most questions, so lead with
        # those rather than truncating from the start and losing them behind
        # the (already-visible-on-dashboard) metrics preamble.
        marker = "Relevant report excerpts:"
        if marker in context:
            excerpts = context.split(marker, 1)[1].strip()
        else:
            excerpts = context.strip()

        snippet = excerpts
        if len(snippet) > 1500:
            snippet = snippet[:1500] + "..."
        return (
            "Offline mode (no LLM API key configured) — showing the most relevant "
            f"excerpt(s) retrieved for your question instead of a generated answer:\n\n"
            f"{snippet}\n\n"
            "Add an ANTHROPIC_API_KEY to get direct, generated answers to questions "
            "like this."
        )


def get_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.llm_configured:
        return AnthropicLLMClient(settings)
    return OfflineLLMClient()
