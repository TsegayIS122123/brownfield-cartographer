"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_codebase_path(tmp_path):
    """Create a temporary sample codebase for testing."""
    codebase = tmp_path / "sample_repo"
    codebase.mkdir()

    # Create sample Python file
    py_file = codebase / "sample.py"
    py_file.write_text(
        """
def hello():
    return "world"

class Test:
    def method(self):
        pass
"""
    )

    # Create sample SQL file
    sql_file = codebase / "query.sql"
    sql_file.write_text(
        """
SELECT * FROM users JOIN orders ON users.id = orders.user_id
"""
    )

    return codebase
