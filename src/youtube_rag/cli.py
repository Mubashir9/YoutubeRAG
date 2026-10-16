"""Starter command-line interface."""
import typer
from .config import Settings
app = typer.Typer(help="Local transcript RAG assistant.")
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
def main() -> None: app()

