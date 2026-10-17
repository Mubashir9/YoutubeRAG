"""Command-line interface."""
from pathlib import Path
import typer
from .config import Settings
from .transcript import VIDEO_ID, process_transcript
from .acquisition import CaptionAcquisitionError, fetch_captions
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
def validate_transcript(source: Path = Path("transcript.json"), video_id: str = VIDEO_ID) -> None:
    """Validate and clean one supplied timestamped transcript."""
    root = Path.cwd()
    diagnostics = process_transcript(
        source,
        root / "data" / "raw" / f"{video_id}.json",
        root / "data" / "processed" / "segments.jsonl",
        root / "data" / "diagnostics" / f"{video_id}.json",
        video_id,
    )
    typer.echo(f"Validated {diagnostics.input_count} records; kept {diagnostics.kept_count}; dropped {diagnostics.dropped_count}.")
    typer.echo(f"Words: {diagnostics.kept_word_count}; range: {diagnostics.start_sec:.3f}s–{diagnostics.end_sec:.3f}s")
    typer.echo(f"Diagnostics: data/diagnostics/{video_id}.json")
def main() -> None: app()

