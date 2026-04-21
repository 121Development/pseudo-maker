"""PyInstaller entrypoint — wraps the CLI so absolute imports work."""
from pseudo_maker.cli import app

if __name__ == "__main__":
    app()
