"""PyInstaller entrypoint — wraps the CLI so absolute imports work."""
from mutable_cosmos.cli import app

if __name__ == "__main__":
    app()
