`uv pip install -e .` - installs the project locally in editable mode \
`pytest -v` - running tests \
`pre-commit run --all-files` - running all precommit hooks \
`pyright src/ocr_kul` - running typing checks with pyright

Run the CLI commands: \
`ocr process <image>` - extracts text \
`ocr batch <directory> -o results.txt` - processes multiple images \
`ocr enhance <image> -o <dir>` - saves preprocessed images

Before you finish this task, ensure that all of these pass \
   ```bash
   pytest -v                      # All 49 tests pass
   pyright src/ocr_kul            # no errors errors and less than 10 warnings
   pre-commit run --all-files     # All hooks pass
   ```
