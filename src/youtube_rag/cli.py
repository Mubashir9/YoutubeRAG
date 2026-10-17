"""Command-line interface."""
from pathlib import Path
import json
import typer
from .config import Settings
from .transcript import VIDEO_ID, process_transcript
from .acquisition import CaptionAcquisitionError, fetch_captions
from .chunking import SequentialWordChunker, load_segments, write_chunks
from .embeddings import LocalEmbedder
from .retrieval import ChromaIndex
from .answering import OpenAIProvider, answer_question
app = typer.Typer(help="Local transcript RAG assistant.")

@app.command("fetch-transcript")
def fetch_transcript(source: str, output_dir: Path = Path("data/raw")) -> None:
    """Fetch available YouTube captions; never download media or transcribe audio."""
    try:
        result = fetch_captions(source, Path.cwd() / output_dir)
    except CaptionAcquisitionError as exc:
        typer.echo(f"Caption retrieval failed: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Retrieved {result.caption_count} caption records for {result.video_id} ({result.caption_kind or 'unknown'}).")
    typer.echo(f"Saved: {output_dir / (result.video_id + '.json')}")
    typer.echo("Next: run validate-transcript with this file to create canonical Phase 2 output.")
@app.command()
def status() -> None:
    """Show configuration and scaffold state."""
    s = Settings.from_env()
    typer.echo("Anthony Mantello Creator RAG — scaffold ready")
    typer.echo(f"Embedding model: {s.embedding_model}")
    typer.echo(f"Index directory: {s.index_dir}")
    typer.echo(f"Top-k: {s.top_k}")
    typer.echo(f"Generation: {'configured' if s.openai_api_key else 'retrieval-only (no API key)'}")
    typer.echo("Indexing and querying arrive in later phases.")

@app.command("validate-transcript")
def validate_transcript(source: Path = Path("data/raw/b76rDd9FYeY.json"), video_id: str = VIDEO_ID) -> None:
    """Validate and clean one supplied timestamped transcript."""
    root = Path.cwd()
    diagnostics = process_transcript(
        source,
        root / "data" / "raw" / f"{video_id}.json",
        root / "data" / "processed" / f"{video_id}.segments.jsonl",
        root / "data" / "diagnostics" / f"{video_id}.json",
        video_id,
    )
    typer.echo(f"Validated {diagnostics.input_count} records; kept {diagnostics.kept_count}; dropped {diagnostics.dropped_count}.")
    typer.echo(f"Words: {diagnostics.kept_word_count}; range: {diagnostics.start_sec:.3f}s–{diagnostics.end_sec:.3f}s")
    typer.echo(f"Diagnostics: data/diagnostics/{video_id}.json")

@app.command("chunk-transcript")
def chunk_transcript(segments: Path = Path("data/processed/segments.jsonl"), video_id: str = VIDEO_ID,
                     output: Path = Path("data/processed/b76rDd9FYeY.chunks.jsonl"), target_words: int = 200,
                     overlap_words: int = 35, max_words: int = 300) -> None:
    """Build deterministic timestamp-aware word-window chunks."""
    chunker = SequentialWordChunker(target_words, overlap_words, max_words)
    chunks, stats = chunker.chunk(load_segments(segments), video_id)
    write_chunks(output, chunks)
    typer.echo(f"Chunked {stats.input_segments} segments into {stats.chunk_count} chunks.")
    typer.echo(f"Words: {stats.word_count}; average: {stats.average_words:.1f}; maximum: {stats.maximum_words}; overlap: {stats.overlap_words}.")
    typer.echo(f"Chunks: {output}")

@app.command("index-chunks")
def index_chunks(chunks: Path = Path("data/processed/chunks.jsonl")) -> None:
    """Embed chunks and idempotently persist them in the local vector index."""
    settings = Settings.from_env()
    rows = [json.loads(line) for line in chunks.read_text(encoding="utf-8").splitlines() if line.strip()]
    from .chunking import Chunk
    index = ChromaIndex(settings.index_dir, LocalEmbedder(settings.embedding_model))
    count = index.upsert([Chunk(**row) for row in rows])
    typer.echo(f"Indexed {count} chunks. Statistics: {index.stats()}")

@app.command("query")
def query(text: str, top_k: int | None = None) -> None:
    """Retrieve timestamped evidence without requiring an LLM key."""
    settings = Settings.from_env()
    results = ChromaIndex(settings.index_dir, LocalEmbedder(settings.embedding_model)).query(text, top_k or settings.top_k)
    for n, result in enumerate(results, 1):
        typer.echo(f"{n}. {result.chunk_id} distance={result.score:.4f} {result.timestamp_url}\n   {result.excerpt}")

@app.command("answer")
def answer(text: str, top_k: int | None = None) -> None:
    """Answer from retrieved evidence, or abstain when evidence is insufficient."""
    settings = Settings.from_env()
    results = ChromaIndex(settings.index_dir, LocalEmbedder(settings.embedding_model)).query(text, top_k or settings.top_k)
    provider = OpenAIProvider(settings.openai_api_key, settings.openai_model) if settings.openai_api_key else None
    result = answer_question(text, results, provider)
    typer.echo(result.text)
    typer.echo(f"Insufficient evidence: {result.insufficient_evidence}")
    for citation in result.citations:
        typer.echo(f"[{citation.chunk_id}] {citation.url}\n  {citation.excerpt}")
def main() -> None: app()

