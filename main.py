import argparse
import sys
import logging
from pathlib import Path
from typing import List
from src.ocr_kul.ocr_service import OcrService
from src.ocr_kul.file_manager import get_image_paths, save_json, save_text
from src.ocr_kul.config import DEFAULT_OUTPUT_DIR


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
        stream=sys.stdout
    )


logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('-l', '--lang', default='eng')
    parser.add_argument('-t', '--timeout', type=int, default=30)

    args = parser.parse_args()

    try:
        logger.info(f"Start processing: {args.input}")

        image_paths: List[Path] = get_image_paths(args.input)
        logger.info(f"Found {len(image_paths)} images")

        processor = OcrService(lang=args.lang, timeout=args.timeout)
        output_data = processor.process_batch(image_paths)

        output_dir = Path(args.output)

        json_path = output_dir / 'results.json'
        save_json(output_data.__dict__, json_path)
        all_text_parts: List[str] = []
        for result in output_data['results']:
            if result['text']:
                all_text_parts.append(f"--- FILE: {result['filename']} ---")
                all_text_parts.append(result['text'])
                all_text_parts.append("")

        all_text: str = '\n'.join(all_text_parts)
        txt_path = output_dir / 'results.txt'
        save_text(all_text, txt_path)

        md_path = output_dir / 'results.md'
        save_text(all_text, md_path)

        logger.info(f"Results saved to: {output_dir}")
        logger.info(
            f"Successes: {output_data['metadata']['successful']}, Errors: {output_data['metadata']['failed']}, Time: {output_data['metadata']['total_processing_time']:.2f}s"
        )

        return 0

    except FileNotFoundError as e:
        logger.error(f"✗ File Not Found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"✗ Value Error: {e}")
        return 1
    except RuntimeError as e:
        logger.critical(f"✗ Runtime Error (Tesseract issue): {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("✗ Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
