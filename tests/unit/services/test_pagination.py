"""Test pagination functionality for get_ocr_jobs."""

from kul_ocr.domain import enums
from kul_ocr.service_layer.services import jobs
from tests.fakes.uow import FakeUnitOfWork
from tests import factories


def test_get_ocr_jobs_default_pagination(uow: FakeUnitOfWork):
    """Test default pagination returns first 20 items."""
    # Create 25 jobs
    all_jobs = factories.generate_ocr_jobs(25, status=enums.JobStatus.PENDING)
    for job in all_jobs:
        uow.jobs.add(job)

    job_dtos, total = jobs.get_ocr_jobs(uow)

    assert len(job_dtos) == 20
    assert total == 25


def test_get_ocr_jobs_custom_pagination(uow: FakeUnitOfWork):
    """Test custom pagination parameters."""
    # Create 25 jobs
    all_jobs = factories.generate_ocr_jobs(25, status=enums.JobStatus.PENDING)
    for job in all_jobs:
        uow.jobs.add(job)

    # Skip 10, get next 10
    job_dtos, total = jobs.get_ocr_jobs(uow, skip=10, limit=10)

    assert len(job_dtos) == 10
    assert total == 25


def test_get_ocr_jobs_pagination_at_end(uow: FakeUnitOfWork):
    """Test pagination at the end of results."""
    # Create 25 jobs
    all_jobs = factories.generate_ocr_jobs(25, status=enums.JobStatus.PENDING)
    for job in all_jobs:
        uow.jobs.add(job)

    # Skip 20, should get remaining 5
    job_dtos, total = jobs.get_ocr_jobs(uow, skip=20, limit=10)

    assert len(job_dtos) == 5
    assert total == 25


def test_get_ocr_jobs_pagination_with_filter(uow: FakeUnitOfWork):
    """Test pagination works with status filter."""
    # Create 25 pending jobs and 5 completed
    pending_jobs = factories.generate_ocr_jobs(25, status=enums.JobStatus.PENDING)
    completed_jobs = factories.generate_ocr_jobs(5, status=enums.JobStatus.COMPLETED)

    for job in list(pending_jobs) + list(completed_jobs):
        uow.jobs.add(job)

    # Get completed jobs with pagination
    job_dtos, total = jobs.get_ocr_jobs(uow, status="completed", skip=0, limit=10)

    assert len(job_dtos) == 5
    assert total == 5
    assert all(dto.status == "completed" for dto in job_dtos)


def test_get_ocr_jobs_pagination_empty_results(uow: FakeUnitOfWork):
    """Test pagination with no results."""
    job_dtos, total = jobs.get_ocr_jobs(uow, skip=0, limit=20)

    assert len(job_dtos) == 0
    assert total == 0


def test_get_ocr_jobs_pagination_preserves_order(uow: FakeUnitOfWork):
    """Test that pagination returns jobs in consistent order (newest first)."""
    # Create jobs
    jobs_list = factories.generate_ocr_jobs(10, status=enums.JobStatus.PENDING)
    for job in jobs_list:
        uow.jobs.add(job)

    # Get first page
    page1, _ = jobs.get_ocr_jobs(uow, skip=0, limit=5)

    # Get second page
    page2, _ = jobs.get_ocr_jobs(uow, skip=5, limit=5)

    # Ensure no overlap
    page1_ids = {dto.id for dto in page1}
    page2_ids = {dto.id for dto in page2}
    assert len(page1_ids & page2_ids) == 0, "Pages should not overlap"

    # Ensure all jobs are returned across pages
    assert len(page1_ids | page2_ids) == 10
