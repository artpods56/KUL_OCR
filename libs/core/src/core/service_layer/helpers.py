import uuid


def generate_id() -> str:
    """Generates a unique identifier as a string.

    Creates a random UUID (version 4) used as an identifier for documents
    and OCR jobs within the system.

    Returns:
        A unique identifier represented as a string.
    """
    return str(uuid.uuid4())
