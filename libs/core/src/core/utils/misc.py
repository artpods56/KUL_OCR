import uuid

from beartype import BeartypeConf, BeartypeStrategy, beartype

# this decorator is used to disable beartype checks on specific classes that cause problems
nobeartype = beartype(conf=BeartypeConf(strategy=BeartypeStrategy.O0))


def generate_id() -> str:
    """Generates a unique identifier as a string.

    Creates a random UUID (version 4) used as an identifier for documents
    and OCR jobs within the system.

    Returns:
        A unique identifier represented as a string.
    """
    return str(uuid.uuid4())
