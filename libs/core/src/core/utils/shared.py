from pathlib import Path


def _find_by_marker(start: Path, marker: str) -> Path | None:
    """Look upwards for ``pyproject.toml`` as a repository marker."""
    for parent in [start, *start.parents]:
        if (parent / marker).is_file():
            return parent
    return None


REPO_ROOT_MARKERS = ["pyproject.toml", ".git", ".gitignore"]


def find_repository_root(start: str | Path | None = None) -> Path:
    path = Path(start or __file__).resolve()
    for marker in REPO_ROOT_MARKERS:
        if marker_root := _find_by_marker(path, marker):
            return marker_root

    raise RuntimeError(
        "Could not find project root. Ensure project includes project.toml file or set PROJECT_ROOT environmental variable."
    )


REPO_ROOT: Path = find_repository_root()
