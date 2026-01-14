from kul_ocr.domain.model import Document, FileType
from kul_ocr.service_layer.helpers import generate_id
from kul_ocr.service_layer.uow import SqlAlchemyUnitOfWork


def test_can_add_and_retrieve_document(uow: SqlAlchemyUnitOfWork):
    """Test adding a document to the database and retrieving it"""
    document_id = generate_id()
    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    with uow:
        uow.documents.add(document)
        uow.commit()

    # Retrieve in a new transaction
    with uow:
        retrieved = uow.documents.get(document_id)
        assert retrieved is not None
        assert retrieved.id == document_id
        assert retrieved.file_path == "/path/to/test.pdf"
        assert retrieved.file_type == FileType.PDF
        assert retrieved.file_size_bytes == 1024


def test_can_list_all_documents(uow: SqlAlchemyUnitOfWork):
    """Test listing all documents from the database"""
    document_ids = [generate_id() for _ in range(3)]
    documents = [
        Document(
            id=document_ids[i],
            file_path=f"/path/to/test{i + 1}.pdf",
            file_type=FileType.PDF,
            file_size_bytes=1024 * (i + 1),
        )
        for i in range(3)
    ]

    with uow:
        for doc in documents:
            uow.documents.add(doc)
        uow.commit()

    # Retrieve in a new transaction
    with uow:
        all_docs = uow.documents.list_all()
        assert len(all_docs) == 3
        assert {doc.id for doc in all_docs} == set(document_ids)


def test_get_returns_none_for_nonexistent_document(uow: SqlAlchemyUnitOfWork):
    """Test that get returns None for a document that doesn't exist"""
    with uow:
        result = uow.documents.get("nonexistent-id")
        assert result is None


def test_document_persists_different_file_types(uow: SqlAlchemyUnitOfWork):
    """Test that documents with different file types are persisted correctly"""
    pdf_id = generate_id()
    png_id = generate_id()
    jpg_id = generate_id()

    documents = [
        Document(
            id=pdf_id,
            file_path="/path/to/test.pdf",
            file_type=FileType.PDF,
            file_size_bytes=1024,
        ),
        Document(
            id=png_id,
            file_path="/path/to/image.png",
            file_type=FileType.PNG,
            file_size_bytes=2048,
        ),
        Document(
            id=jpg_id,
            file_path="/path/to/photo.jpg",
            file_type=FileType.JPG,
            file_size_bytes=3072,
        ),
    ]

    with uow:
        for doc in documents:
            uow.documents.add(doc)
        uow.commit()

    # Verify each document
    with uow:
        pdf_doc = uow.documents.get(pdf_id)
        assert pdf_doc is not None
        assert pdf_doc.file_type == FileType.PDF

        png_doc = uow.documents.get(png_id)
        assert png_doc is not None
        assert png_doc.file_type == FileType.PNG

        jpg_doc = uow.documents.get(jpg_id)
        assert jpg_doc is not None
        assert jpg_doc.file_type == FileType.JPG
