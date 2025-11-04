import json
from pathlib import Path
from typing import List
from src.ocr_kul.config import SUPPORTED_FORMATS


def get_image_paths(input_path: str) -> List[Path]:
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {input_path}")

    if path.is_file():
        if path.suffix.lower() in SUPPORTED_FORMATS:
            return [path]
        else:
            raise ValueError(
                f"Unsupported format: {path.suffix}. "
                f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )

    images = []
    for ext in SUPPORTED_FORMATS:
        images.extend(path.glob(f"*{ext}"))
    if not images:
        raise ValueError(f"No images found in: {input_path}")

    return sorted(images)


def save_json(data: dict, output_path: Path) -> None:

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_text(text: str, output_path: Path) -> None:

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)