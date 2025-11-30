"""Test that the project setup is correct."""

import pytest
from pathlib import Path


def test_config_settings_import():
    """Test that settings can be imported."""
    from config.settings import settings
    assert settings is not None
    assert settings.bedrock_model_id == "amazon.nova-pro-v1:0"
    assert settings.aws_region == "us-east-1"


def test_api_main_import():
    """Test that FastAPI app can be imported."""
    from api.main import app
    assert app is not None
    assert app.title == "Code Review & Documentation Agent"


def test_cli_import():
    """Test that CLI can be imported."""
    from api.cli import main
    assert main is not None


def test_directory_structure():
    """Test that all required directories exist."""
    required_dirs = [
        "agents",
        "models",
        "tools",
        "api",
        "config",
        "tests",
        "examples",
    ]
    
    for dir_name in required_dirs:
        path = Path(dir_name)
        assert path.exists(), f"Directory '{dir_name}' should exist"
        assert path.is_dir(), f"'{dir_name}' should be a directory"


def test_required_files():
    """Test that all required files exist."""
    required_files = [
        "pyproject.toml",
        "requirements.txt",
        "README.md",
        ".env.example",
        ".gitignore",
        "Dockerfile",
        "docker-compose.yml",
        "config/settings.py",
        "api/main.py",
        "api/cli.py",
    ]
    
    for file_name in required_files:
        path = Path(file_name)
        assert path.exists(), f"File '{file_name}' should exist"
        assert path.is_file(), f"'{file_name}' should be a file"


def test_api_endpoints():
    """Test that API endpoints are defined."""
    from api.main import app
    
    routes = [route.path for route in app.routes]
    
    assert "/" in routes
    assert "/health" in routes
    assert "/analyze" in routes
    assert "/status/{session_id}" in routes
    assert "/pause/{session_id}" in routes
    assert "/resume/{session_id}" in routes
    assert "/results/{session_id}" in routes
    assert "/history" in routes
