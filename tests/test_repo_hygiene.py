import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_PATTERN = re.compile(r"gsk_[A-Za-z0-9]{20,}")


def read_lines(name: str) -> list[str]:
    return (ROOT / name).read_text(encoding="utf-8-sig").splitlines()


def test_env_file_is_ignored_by_git_and_docker():
    assert ".env" in read_lines(".gitignore")
    assert ".env" in read_lines(".dockerignore")


def test_no_api_key_in_repository_files():
    patterns = ["src/**/*.py", "tests/**/*.py", "*.md", "*.yml", "*.json",
                "Dockerfile", ".github/**/*.yml", "evaluation/*.md", "evaluation/*.json"]
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                assert not KEY_PATTERN.search(text), f"clé API trouvée dans {path}"