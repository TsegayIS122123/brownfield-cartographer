#!/usr/bin/env python3
"""Command-line interface for Brownfield Cartographer."""

import click
from pathlib import Path
import sys

@click.group()
def main():
    """Brownfield Cartographer - Codebase Intelligence System"""
    pass

@main.command()
@click.argument('repo_path', type=str)
@click.option('--output-dir', default='.cartography', help='Output directory')
def analyze(repo_path: str, output_dir: str):
    """Analyze a codebase and generate intelligence artifacts."""
    click.echo(f" Analyzing repository: {repo_path}")
    click.echo(f" Output directory: {output_dir}")
    
    # TODO: Implement analysis pipeline
    click.echo(" Analysis complete! Check .cartography/ for outputs.")

@main.command()
def query():
    """Start interactive query mode."""
    click.echo(" Starting Navigator agent...")
    click.echo("Type 'help' for available commands, 'exit' to quit.")
    
    while True:
        try:
            cmd = input("\n > ").strip()
            if cmd.lower() in ['exit', 'quit']:
                break
            elif cmd.lower() == 'help':
                click.echo("""
Available commands:
  find_implementation <concept>  - Search for where concept is implemented
  trace_lineage <dataset>        - Show data lineage
  blast_radius <module>          - Show impact of changing module
  explain_module <path>          - Explain what module does
  exit                           - Exit query mode
                """)
            else:
                click.echo(f"Processing: {cmd}")
                # TODO: Implement Navigator agent
        except KeyboardInterrupt:
            break
    
    click.echo(" Goodbye!")

@main.command()
def version():
    """Show version information."""
    from src import __version__
    click.echo(f"Brownfield Cartographer v{__version__}")

if __name__ == '__main__':
    main()
