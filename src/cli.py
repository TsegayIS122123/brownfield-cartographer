#!/usr/bin/env python3
"""Command-line interface for Brownfield Cartographer."""

import os
import sys
import json
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
@click.option('--incremental', is_flag=True, help='Run incremental update (only changed files)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def analyze(repo_path: str, output_dir: str, incremental: bool, verbose: bool):
    """Analyze a codebase and generate intelligence artifacts."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    click.echo("🔍 Brownfield Cartographer - Full Pipeline Analysis")
    click.echo(f"📁 Repository: {repo_path}")
    click.echo(f"📂 Output directory: {output_dir}")
    if incremental:
        click.echo("⚡ Incremental mode: ON")
    
    # Convert relative path to absolute
    repo_path = str(Path(repo_path).resolve())
    
    # Handle GitHub URLs
    if repo_path.startswith(('http://', 'https://', 'git@')):
        click.echo("🌐 Detected remote repository. Cloning locally...")
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
    
    click.echo("\n🚀 Starting analysis...")
    orchestrator = Phase1Orchestrator(repo_path, output_dir)
    
    try:
        results = orchestrator.run(incremental=incremental)
        
        # Extract summary data safely
        summary = results.get("summary", {})
        surveyor_data = summary.get("surveyor", {})
        hydrologist_data = summary.get("hydrologist", {})
        semanticist_data = summary.get("semanticist", {})
        
        # Get languages as a string
        languages_dict = surveyor_data.get('languages', {})
        languages_str = ', '.join(languages_dict.keys()) if languages_dict else 'none'
        
        click.echo("\n✅ Analysis pipeline completed!")
        click.echo("📊 Summary:")
        click.echo(f"   • Phase 1 (Surveyor): {'✅' if results.get('surveyor') else '❌'}")
        click.echo(f"   • Phase 2 (Hydrologist): {'✅' if results.get('hydrologist') else '❌'}")
        click.echo(f"   • Phase 3 (Semanticist): {'✅' if results.get('semanticist') else '❌'}")
        click.echo(f"   • Phase 4 (Archivist): {'✅' if results.get('archivist') else '❌'}")
        click.echo("")
        click.echo(f"   • Modules analyzed: {surveyor_data.get('total_modules', 0)}")
        click.echo(f"   • Imports found: {surveyor_data.get('total_imports', 0)}")
        click.echo(f"   • Languages: {languages_str}")
        click.echo(f"   • Python operations: {hydrologist_data.get('python_ops', 0)}")
        click.echo(f"   • Source datasets: {hydrologist_data.get('sources', 0)}")
        click.echo(f"   • Sink datasets: {hydrologist_data.get('sinks', 0)}")
        click.echo(f"   • Purpose statements: {semanticist_data.get('purpose_statements', 0)}")
        click.echo(f"   • LLM cost: ${semanticist_data.get('total_cost', 0):.4f}")
        click.echo(f"\n📁 Artifacts saved to: {output_dir}/")
        click.echo(f"   • module_graph.json")
        click.echo(f"   • surveyor_results.json")
        click.echo(f"   • lineage_graph.json")
        click.echo(f"   • lineage_stats.json")
        click.echo(f"   • semanticist_results.json")
        click.echo(f"   • CODEBASE.md")
        click.echo(f"   • onboarding_brief.md")
        click.echo(f"   • cartography_trace.jsonl")
        
    except Exception as e:
        click.echo(f"❌ Analysis failed: {e}", err=True)
        # Show partial results if available
        if 'results' in locals():
            click.echo("⚠️ Partial results may be available in .cartography/")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option('--cart-dir', default='.cartography', help='Directory containing cartography artifacts')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def query(cart_dir: str, verbose: bool):
    """Start interactive Navigator query mode."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    click.echo("🎮 Brownfield Cartographer - Navigator Query Mode")
    click.echo(f"📁 Using artifacts from: {cart_dir}")
    click.echo("=" * 60)
    
    # Check if artifacts exist
    cart_path = Path(cart_dir)
    if not cart_path.exists():
        click.echo(f"❌ Cartography directory not found: {cart_dir}")
        click.echo("   Please run analysis first: python -m src.cli analyze <repo>")
        return
    
    # Load necessary artifacts
    try:
        from src.graph.knowledge_graph import KnowledgeGraph
        from src.graph.lineage_graph import LineageGraph
        from src.agents.navigator import NavigatorAgent
        from src.agents.archivist import ArchivistAgent
        
        click.echo("\n📂 Loading artifacts...")
        
        # Load knowledge graph
        kg_path = cart_path / "knowledge_graph.json"
        if kg_path.exists():
            knowledge_graph = KnowledgeGraph.load_json(str(kg_path))
            click.echo(f"   ✅ Knowledge graph: {knowledge_graph.graph.number_of_nodes()} nodes, {knowledge_graph.graph.number_of_edges()} edges")
        else:
            # Try module graph as fallback
            module_path = cart_path / "module_graph.json"
            if module_path.exists():
                knowledge_graph = KnowledgeGraph.load_json(str(module_path))
                click.echo(f"   ✅ Module graph loaded (fallback): {knowledge_graph.graph.number_of_nodes()} nodes")
            else:
                knowledge_graph = KnowledgeGraph()
                click.echo("   ⚠️ No graph found, using empty graph")
        
        # Load lineage graph
        lineage_path = cart_path / "lineage_graph.json"
        if lineage_path.exists():
            lineage_graph = LineageGraph.from_json(str(lineage_path))
            click.echo(f"   ✅ Lineage graph: {lineage_graph.graph.number_of_nodes()} nodes, {lineage_graph.graph.number_of_edges()} edges")
        else:
            lineage_graph = None
            click.echo("   ⚠️ Lineage graph not found")
        
        # Load semanticist results
        semantic_path = cart_path / "semanticist_results.json"
        if semantic_path.exists():
            with open(semantic_path, 'r', encoding='utf-8') as f:
                semanticist_results = json.load(f)
            purposes = len(semanticist_results.get("purpose_statements", {}))
            click.echo(f"   ✅ Semanticist results: {purposes} purpose statements")
        else:
            semanticist_results = {}
            click.echo("   ⚠️ Semanticist results not found")
        
        # Initialize archivist for logging
        archivist = ArchivistAgent(output_dir=cart_dir)
        
        # Initialize navigator
        navigator = NavigatorAgent(
            knowledge_graph=knowledge_graph,
            lineage_graph=lineage_graph,
            semanticist_results=semanticist_results,
            archivist=archivist
        )
        
        click.echo("\n✅ Navigator ready! Type 'help' for commands, 'exit' to quit.\n")
        
        # Start interactive mode
        navigator.interactive_mode()
        
    except ImportError as e:
        click.echo(f"❌ Failed to import Navigator dependencies: {e}")
        click.echo("   Please install: uv pip install langgraph langchain-core")
    except Exception as e:
        click.echo(f"❌ Failed to initialize Navigator: {e}")
        if verbose:
            import traceback
            traceback.print_exc()


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