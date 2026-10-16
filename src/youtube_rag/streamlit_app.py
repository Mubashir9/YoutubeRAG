"""Starter Streamlit UI."""
import streamlit as st
from .config import Settings
def run() -> None:
    s = Settings.from_env()
    st.set_page_config(page_title="Anthony Mantello Creator RAG")
    st.title("Anthony Mantello Creator RAG")
    st.caption("Searches only locally indexed, supplied transcript material.")
    st.info("Scaffold ready. Validation, indexing, and answering arrive in later phases.")
    st.text_input("Question", placeholder="Ask about an indexed video")
    if not s.openai_api_key: st.warning("No OpenAI API key configured. Retrieval-only operation remains available.")
    st.write({"embedding_model": s.embedding_model, "top_k": s.top_k, "index_dir": str(s.index_dir)})
if __name__ == "__main__": run()

