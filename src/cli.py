#!/usr/bin/env python3
"""Command-line interface for Brownfield Cartographer."""

import os
import sys
import logging
from pathlib import Path

import click

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def main():
    """Brownfield Cartographer - Codebase Intelligence System"""
    pass


@main.command()
@click.argument('repo_path', type=str)
@click.option('--output-dir', default='.cartography', help='Output directory')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def analyze(repo_path: str, output_dir: str, verbose: bool):
    """Analyze a codebase and generate intelligence artifacts."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    click.echo(" Brownfield Cartographer - Phase 1/2 Analysis")
    click.echo(f" Repository: {repo_path}")
    click.echo(f" Output directory: {output_dir}")
    
    # Convert relative path to absolute
    repo_path = str(Path(repo_path).resolve())
    
    # Handle GitHub URLs
    if repo_path.startswith(('http://', 'https://', 'git@')):
        click.echo("Detected remote repository. Cloning locally...")
        local_path = clone_repository(repo_path)
        if not local_path:
            click.echo("❌ Failed to clone repository", err=True)
            sys.exit(1)
        repo_path = local_path
        click.echo(f"✅ Cloned to: {repo_path}")
    
    # Ensure path exists
    if not os.path.exists(repo_path):
        click.echo(f"❌ Path does not exist: {repo_path}", err=True)
        sys.exit(1)
    
    # Run analysis
    try:
        from src.orchestrator import Phase1Orchestrator
    except ImportError as e:
        click.echo(f"❌ Failed to import orchestrator: {e}", err=True)
        sys.exit(1)
    
    click.echo("\n Starting analysis...")
    orchestrator = Phase1Orchestrator(repo_path, output_dir)
    
    try:
        results = orchestrator.run()
        
        # Extract summary data safely
        summary = results.get("summary", {})
        surveyor_data = summary.get("surveyor", {})
        hydrologist_data = summary.get("hydrologist", {})
        
        # Get languages as a string
        languages_dict = surveyor_data.get('languages', {})
        languages_str = ', '.join(languages_dict.keys()) if languages_dict else 'none'
        
        click.echo("\n✅ Analysis complete!")
        click.echo("📊 Summary:")
        click.echo(f"   • Modules analyzed: {surveyor_data.get('total_modules', 0)}")
        click.echo(f"   • Imports found: {surveyor_data.get('total_imports', 0)}")  # Will now show correct count!
        click.echo(f"   • Languages: {languages_str}")
        click.echo(f"   • Python operations: {hydrologist_data.get('python_ops', 0)}")
        click.echo(f"   • Source datasets: {hydrologist_data.get('sources', 0)}")
        click.echo(f"   • Sink datasets: {hydrologist_data.get('sinks', 0)}")
        click.echo(f"\n📁 Artifacts saved to: {output_dir}/")
        click.echo(f"   • module_graph.json")
        click.echo(f"   • surveyor_results.json")
        click.echo(f"   • lineage_graph.json")
        click.echo(f"   • lineage_stats.json")
        
    except Exception as e:
        click.echo(f"❌ Analysis failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
def version():
    """Show version information."""
    try:
        from src import __version__
        click.echo(f"Brownfield Cartographer v{__version__}")
    except ImportError:
        click.echo("Brownfield Cartographer v0.1.0")


def clone_repository(repo_url: str) -> str:
    """Clone a git repository to a temporary directory."""
    import tempfile
    from git import Repo
    
    temp_dir = tempfile.mkdtemp(prefix="cartographer_")
    try:
        click.echo(f"⏳ Cloning {repo_url}...")
        Repo.clone_from(repo_url, temp_dir)
        return temp_dir
    except Exception as e:
        logger.error(f"Clone failed: {e}")
        return None


if __name__ == '__main__':
    main()