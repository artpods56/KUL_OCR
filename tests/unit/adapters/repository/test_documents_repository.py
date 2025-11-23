from pathlib import Path

from ocr_kul.adapters.database.repository import FakeDocumentRepository
from ocr_kul.domain.model import Document, FileType
from tests import factories


class TestDocumentRepository:
    def test_add_and_get_document(
        self, fake_doc_repo: FakeDocumentRepository, document: Document
    ):
        fake_doc_repo.add(document)
        retrieved = fake_doc_repo.get(document.id)

        assert retrieved is not None
        assert retrieved.id == document.id
        assert retrieved.file_path == document.file_path
        assert retrieved.file_type == document.file_type

    def test_get_nonexistent_document_returns_none(
        self, fake_doc_repo: FakeDocumentRepository
    ):
        result = fake_doc_repo.get("nonexistent-id")

        assert result is None

    def test_add_multiple_documents(
        self, fake_doc_repo: FakeDocumentRepository, tmp_path: Path
    ):
        documents = factories.generate_documents(tmp_path)

        for document in documents:
            fake_doc_repo.add(document)

        for document in documents:
            retrieved_doc = fake_doc_repo.get(document.id)
            assert retrieved_doc is not None
            assert retrieved_doc.id == document.id

    def test_list_all_empty_repository(self, fake_doc_repo: FakeDocumentRepository):
        documents = fake_doc_repo.list_all()

        assert documents == []

    def test_list_all_documents(
        self, fake_doc_repo: FakeDocumentRepository, tmp_path: Path
    ):
        doc1 = factories.generate_document(tmp_path, file_type=FileType.PDF)
        doc2 = factories.generate_document(tmp_path, file_type=FileType.PNG)

        fake_doc_repo.add(doc1)
        fake_doc_repo.add(doc2)

        documents = fake_doc_repo.list_all()

        assert len(documents) == 2
        assert doc1 in documents
        assert doc2 in documents

    def test_overwrite_existing_document(
        self, fake_doc_repo: FakeDocumentRepository, tmp_path: Path
    ):
        # Create two documents with same ID but different data
        doc1 = factories.generate_document(tmp_path, file_type=FileType.PDF)
        doc2 = factories.generate_document(tmp_path, file_type=FileType.PNG)
        doc2.id = doc1.id  # Use same ID to test overwrite

        fake_doc_repo.add(doc1)
        fake_doc_repo.add(doc2)

        retrieved = fake_doc_repo.get(doc1.id)
        assert retrieved is not None
        assert retrieved.file_path == doc2.file_path
        assert retrieved.file_type == doc2.file_type
        assert len(fake_doc_repo.list_all()) == 1
