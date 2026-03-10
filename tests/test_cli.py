"""Tests for CLI interface."""

from click.testing import CliRunner

from src.cli import main


def test_cli_help():
    """Test that CLI help works."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Brownfield Cartographer" in result.output


def test_cli_version():
    """Test version command."""
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert "v0.1.0" in result.output
