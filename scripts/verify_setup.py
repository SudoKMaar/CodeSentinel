"""Verify that the project setup is correct."""

import sys
from pathlib import Path


def check_directories() -> bool:
    """Check that all required directories exist."""
    required_dirs = [
        "agents",
        "models",
        "tools",
        "api",
        "config",
        "tests",
        "examples",
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        path = Path(dir_name)
        if path.exists() and path.is_dir():
            print(f"✓ Directory '{dir_name}' exists")
        else:
            print(f"✗ Directory '{dir_name}' missing")
            all_exist = False
    
    return all_exist


def check_files() -> bool:
    """Check that all required files exist."""
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
    
    all_exist = True
    for file_name in required_files:
        path = Path(file_name)
        if path.exists() and path.is_file():
            print(f"✓ File '{file_name}' exists")
        else:
            print(f"✗ File '{file_name}' missing")
            all_exist = False
    
    return all_exist


def check_imports() -> bool:
    """Check that key dependencies can be imported."""
    dependencies = [
        ("pydantic", "Pydantic"),
        ("pydantic_settings", "Pydantic Settings"),
        ("fastapi", "FastAPI"),
        ("click", "Click"),
        ("structlog", "Structlog"),
    ]
    
    all_importable = True
    for module_name, display_name in dependencies:
        try:
            __import__(module_name)
            print(f"✓ {display_name} can be imported")
        except ImportError:
            print(f"✗ {display_name} cannot be imported (run 'pip install -e .')")
            all_importable = False
    
    return all_importable


def main() -> int:
    """Run all verification checks."""
    print("=" * 60)
    print("Code Review & Documentation Agent - Setup Verification")
    print("=" * 60)
    print()
    
    print("Checking directories...")
    dirs_ok = check_directories()
    print()
    
    print("Checking files...")
    files_ok = check_files()
    print()
    
    print("Checking dependencies...")
    imports_ok = check_imports()
    print()
    
    print("=" * 60)
    if dirs_ok and files_ok and imports_ok:
        print("✓ All checks passed! Setup is complete.")
        print()
        print("Next steps:")
        print("  1. Copy .env.example to .env and configure your settings")
        print("  2. Run 'pip install -e .' to install the package")
        print("  3. Run 'code-review-agent --help' to see CLI options")
        print("  4. Run 'uvicorn api.main:app --reload' to start the API")
        return 0
    else:
        print("✗ Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
