"""Streamlit UI for the local, evidence-backed transcript assistant."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

import streamlit as st

from .answering import Answer, GroqProvider, OpenAIProvider, answer_question
from .config import Settings
from .embeddings import LocalEmbedder
from .retrieval import ChromaIndex, RetrievalResult

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,32}$")


def valid_video_id(video_id: str) -> bool:
    return bool(VIDEO_ID_RE.fullmatch(video_id))


def embed_url(video_id: str, start_sec: float) -> str | None:
    if not valid_video_id(video_id):
        return None
    return f"https://www.youtube.com/embed/{video_id}?start={max(0, int(start_sec))}&rel=0"


@st.cache_resource(show_spinner=False)
def load_index(index_dir: str, embedding_model: str) -> ChromaIndex:
    return ChromaIndex(Path(index_dir), LocalEmbedder(embedding_model))


def _show_evidence(results: Sequence[RetrievalResult]) -> None:
    st.subheader("Evidence")
    if not results:
        st.info("No matching evidence was found in the indexed corpus.")
        return
    for number, result in enumerate(results, 1):
        with st.container(border=True):
            st.markdown(f"**{number}. {result.start_sec:.1f}s–{result.end_sec:.1f}s · distance {result.score:.3f}**")
            st.write(result.excerpt)
            st.caption(f"Chunk `{result.chunk_id}` · video `{result.video_id}`")
            st.link_button("Open cited moment", result.timestamp_url)


def _show_playback(results: Sequence[RetrievalResult]) -> None:
    safe = [result for result in results if embed_url(result.video_id, result.start_sec)]
    if not safe:
        return
    st.subheader("Playback")
    selected = st.selectbox("Evidence moment", range(len(safe)), format_func=lambda i: f"{safe[i].video_id} · {safe[i].start_sec:.1f}s")
    result = safe[selected]
    url = embed_url(result.video_id, result.start_sec)
    assert url is not None
    st.video(url, start_time=max(0, int(result.start_sec)))
    st.caption("If the embedded player is unavailable, use the external timestamped link.")
    st.link_button("Open on YouTube", result.timestamp_url)


def _show_answer(answer: Answer) -> None:
    st.subheader("Answer")
    (st.warning if answer.insufficient_evidence else st.write)(answer.text)
    if answer.citations:
        st.caption(f"{len(answer.citations)} citation(s) were built from retrieved evidence.")


def run() -> None:
    settings = Settings.from_env()
    st.set_page_config(page_title="Anthony Mantello Creator RAG", page_icon="🔎", layout="wide")
    st.title("Anthony Mantello Creator RAG")
    st.caption("Evidence-backed answers from the locally indexed transcript corpus.")
    st.info("Corpus scope: one supplied transcript (video ID `b76rDd9FYeY`). This app does not represent the whole channel.")
    with st.sidebar:
        st.header("About this index")
        st.write(f"Embedding model: `{settings.embedding_model}`")
        st.write(f"Top results: `{settings.top_k}`")
        configured = settings.groq_api_key if settings.llm_provider == "groq" else settings.openai_api_key
        st.write(f"Generation provider: `{settings.llm_provider}`")
        (st.success if configured else st.warning)(
            "Grounded answer generation is configured." if configured else "No generation API key. Retrieval-only mode is available."
        )
    question = st.chat_input("Ask about the indexed transcript")
    if not question or not question.strip():
        st.write("Ask a question to inspect retrieved transcript evidence and its timestamp.")
        return
    try:
        with st.spinner("Searching the local index…"):
            index = load_index(str(settings.index_dir), settings.embedding_model)
            if index.collection.count() == 0:
                st.error("No transcript chunks are indexed yet. Run `youtube-rag index-chunks` first.")
                return
            results = index.query(question.strip(), settings.top_k)
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        st.error(f"The local index could not be loaded: {exc}. Run `youtube-rag index-chunks` if needed.")
        return
    try:
        provider = (GroqProvider(settings.groq_api_key, settings.groq_model) if settings.llm_provider == "groq" and settings.groq_api_key
                    else OpenAIProvider(settings.openai_api_key, settings.openai_model) if settings.llm_provider == "openai" and settings.openai_api_key else None)
        answer = answer_question(question.strip(), results, provider)
    except Exception as exc:
        st.error(f"Answer generation failed: {exc}")
        answer = answer_question(question.strip(), results)
    _show_answer(answer)
    _show_playback(results)
    _show_evidence(results)


if __name__ == "__main__":
    run()

