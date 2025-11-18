"""Tests for type hint coverage."""

import inspect
import subprocess


def test_pyright_passes():
    """Pyright static type checker must pass with less than 5 errors."""
    result = subprocess.run(
        ["pyright", "src/ocr_kul"],
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Count error lines
    error_count = 0
    for line in output.split("\n"):
        if "error" in line.lower() and "0 error" not in line.lower():
            # Try to extract error count
            parts = line.split()
            for i, part in enumerate(parts):
                if "error" in part.lower() and i > 0:
                    try:
                        error_count = int(parts[i - 1])
                    except (ValueError, IndexError):
                        pass

    assert error_count < 5, (
        f"Too many type errors: {error_count}. "
        f"Fix type hints to reduce errors below 5.\n\nOutput:\n{output}"
    )


def test_engine_module_has_type_hints():
    """engine module functions must have complete type hints."""
    from ocr_kul.engine import TesseractOCREngine

    # Check __init__
    init_sig = inspect.signature(TesseractOCREngine.__init__)
    for param_name, param in init_sig.parameters.items():
        if param_name not in ["self"]:
            assert param.annotation != inspect.Parameter.empty, (
                f"Parameter '{param_name}' in __init__ missing type annotation"
            )

    # Check process
    process_sig = inspect.signature(TesseractOCREngine.process)
    assert process_sig.return_annotation != inspect.Signature.empty, (
        "process() method missing return type annotation"
    )

    for param_name, param in process_sig.parameters.items():
        if param_name != "self":
            assert param.annotation != inspect.Parameter.empty, (
                f"Parameter '{param_name}' in process() missing type annotation"
            )


def test_preprocessing_module_has_type_hints():
    """preprocessing module functions must have complete type hints."""
    import ocr_kul.preprocessing as preprocessing

    functions = [
        preprocessing.enhance_image,
        preprocessing.resize_image,
        preprocessing.binarize_image,
    ]

    for func in functions:
        sig = inspect.signature(func)

        # Check return type
        assert sig.return_annotation != inspect.Signature.empty, (
            f"Function {func.__name__} missing return type annotation"
        )

        # Check parameter types
        for param_name, param in sig.parameters.items():
            assert param.annotation != inspect.Parameter.empty, (
                f"Parameter '{param_name}' in {func.__name__} missing type annotation"
            )


def test_io_utils_module_has_type_hints():
    """io_utils module functions must have complete type hints."""
    import ocr_kul.io_utils as io_utils

    functions = [
        io_utils.load_image,
        io_utils.save_image,
        io_utils.get_image_files,
    ]

    for func in functions:
        sig = inspect.signature(func)

        # Check return type
        assert sig.return_annotation != inspect.Signature.empty, (
            f"Function {func.__name__} missing return type annotation"
        )

        # Check parameter types
        for param_name, param in sig.parameters.items():
            assert param.annotation != inspect.Parameter.empty, (
                f"Parameter '{param_name}' in {func.__name__} missing type annotation"
            )
