"""In-memory vector store for T.C.R.E.I. knowledge retrieval.

Loads knowledge docs, criteria definitions, and domain configs at startup,
chunks them, and provides semantic retrieval for grounding LLM evaluations.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
_CRITERIA_PATH = Path(__file__).parent.parent / "evaluator" / "criteria" / "__init__.py"
_DOMAINS_DIR = Path(__file__).parent.parent / "config" / "defaults" / "domains"


def _get_embeddings() -> Embeddings:
    """Get the Ollama embeddings model (self-hosted, free)."""
    from langchain_ollama import OllamaEmbeddings

    from src.config import get_settings

    settings = get_settings()

    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )


def _load_knowledge_docs() -> list[Document]:
    """Load all markdown files from the knowledge directory."""
    docs = []
    if not _KNOWLEDGE_DIR.exists():
        logger.warning("Knowledge directory not found: %s", _KNOWLEDGE_DIR)
        return docs

    for md_file in sorted(_KNOWLEDGE_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        docs.append(Document(
            page_content=content,
            metadata={"source": str(md_file.name), "type": "knowledge"},
        ))
        logger.debug("Loaded knowledge doc: %s (%d chars)", md_file.name, len(content))

    return docs


def _load_criteria_doc() -> list[Document]:
    """Serialize criteria definitions into a document."""
    docs = []
    if not _CRITERIA_PATH.exists():
        return docs

    try:
        from src.evaluator.criteria import ALL_CRITERIA

        parts = []
        for dimension, criteria_list in ALL_CRITERIA.items():
            criteria_text = "\n".join(
                f"  - {c.name}: {c.description} (weight: {c.weight})"
                for c in criteria_list
            )
            parts.append(f"## {dimension.upper()}\n{criteria_text}")

        content = "# Evaluation Criteria\n\n" + "\n\n".join(parts)
        docs.append(Document(
            page_content=content,
            metadata={"source": "criteria.py", "type": "criteria"},
        ))
    except ImportError:
        logger.warning("Could not import criteria module")

    return docs


def _load_domain_configs() -> list[Document]:
    """Load domain-specific YAML configurations."""
    import yaml

    docs = []
    if not _DOMAINS_DIR.exists():
        return docs

    for yaml_file in sorted(_DOMAINS_DIR.glob("*.yaml")):
        try:
            content = yaml_file.read_text(encoding="utf-8")
            # Parse to validate, then use raw content
            yaml.safe_load(content)
            docs.append(Document(
                page_content=content,
                metadata={"source": str(yaml_file.name), "type": "domain_config"},
            ))
            logger.debug("Loaded domain config: %s", yaml_file.name)
        except (yaml.YAMLError, OSError) as exc:
            logger.warning("Failed to load domain config %s: %s", yaml_file.name, exc)

    return docs


def _build_store(embeddings: Embeddings) -> InMemoryVectorStore:
    """Build the vector store from all knowledge sources."""
    all_docs = _load_knowledge_docs() + _load_criteria_doc() + _load_domain_configs()

    if not all_docs:
        logger.warning("No knowledge documents found — RAG context will be empty")
        return InMemoryVectorStore(embedding=embeddings)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(all_docs)
    logger.info("Built knowledge store with %d chunks from %d documents", len(chunks), len(all_docs))

    store = InMemoryVectorStore.from_documents(chunks, embedding=embeddings)
    return store


@lru_cache(maxsize=1)
def _get_store() -> InMemoryVectorStore:
    """Get or create the singleton vector store."""
    embeddings = _get_embeddings()
    return _build_store(embeddings)


def warmup_knowledge_store() -> None:
    """Eagerly build the knowledge store so it's ready before serving requests.

    Call this at application startup (module-level in ``app.py``) to
    pre-load documents, chunk them, and embed them via Ollama *before*
    Chainlit begins accepting connections.  If Ollama is unreachable or
    any other error occurs the failure is logged and the app continues
    (the store will be retried lazily on first query).
    """
    logger.info("Warming up RAG knowledge store ...")
    try:
        _get_store()
        logger.info("RAG knowledge store ready.")
    except Exception as exc:
        logger.warning(
            "RAG warmup failed (non-fatal, will retry on first query): %s", exc
        )


_MAX_QUERY_CHARS = 6000  # ~1500 tokens — safe for embedding models


async def retrieve_context(query: str, top_k: int = 3) -> str:
    """Retrieve relevant knowledge context for a query.

    Args:
        query: The text to search for relevant context.
        top_k: Number of top results to return.

    Returns:
        A formatted string of relevant context passages, or empty string
        if no relevant context is found.
    """
    try:
        store = _get_store()
        # Truncate long prompts to avoid exceeding embedding model context
        truncated_query = query[:_MAX_QUERY_CHARS] if len(query) > _MAX_QUERY_CHARS else query
        results = store.similarity_search(truncated_query, k=top_k)

        if not results:
            return ""

        passages = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source", "unknown")
            passages.append(f"[{source}] {doc.page_content}")

        return "\n\n---\n\n".join(passages)

    except Exception as exc:
        logger.warning("RAG retrieval failed (non-fatal): %s", exc)
        return ""
