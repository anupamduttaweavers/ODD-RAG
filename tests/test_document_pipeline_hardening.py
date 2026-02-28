"""Regression tests for document ingestion hardening changes."""

from __future__ import annotations

import types
import sys
from pathlib import Path

import pytest
from langchain_core.documents import Document

from app.core.config import settings
from app.filesource import scanner
from app.filesource import service as filesource_service
from app.utils import document_converstion as dc
from app.utils import hash_registry as hr


def test_allowed_extensions_are_consistent_across_ingestion_paths():
    expected = {ext.lower() for ext in settings.ALLOWED_EXTENSIONS}
    assert scanner._ALLOWED_EXT == expected
    assert filesource_service._ALLOWED_EXTENSIONS == expected


def test_pdf_loader_returns_synthetic_page_when_pdf_has_no_pages(monkeypatch):
    class FakeLoader:
        def __init__(self, _path: str):
            pass

        def load(self):
            return []

    monkeypatch.setattr(dc, "PyPDFLoader", FakeLoader)

    pages = dc.load_pdf_with_pages("dummy.pdf")
    assert len(pages) == 1
    assert pages[0].page_content == ""
    assert pages[0].metadata["page_number"] == 1
    assert pages[0].metadata["total_pages"] == 1


def test_pdf_loader_does_not_run_ocr_when_page_already_has_text(monkeypatch):
    class FakeLoader:
        def __init__(self, _path: str):
            pass

        def load(self):
            return [Document(page_content="Short digital text", metadata={})]

    monkeypatch.setattr(dc, "PyPDFLoader", FakeLoader)
    monkeypatch.setattr(dc, "_ocr_page_image", lambda _img: "SHOULD_NOT_BE_USED")

    pages = dc.load_pdf_with_pages("dummy.pdf")
    assert pages[0].page_content == "Short digital text"


def test_pdf_loader_concatenates_ocr_from_multiple_images(monkeypatch):
    class FakeLoader:
        def __init__(self, _path: str):
            pass

        def load(self):
            return [Document(page_content="   ", metadata={})]

    class FakeImageObj:
        def __init__(self, data: bytes):
            self.data = data

    class FakeReader:
        def __init__(self, _path: str):
            self.pages = [types.SimpleNamespace(images=[FakeImageObj(b"a"), FakeImageObj(b"b")])]

    class FakePILImage:
        @staticmethod
        def open(_bytes_io):
            return types.SimpleNamespace(convert=lambda _mode: object())

    monkeypatch.setattr(dc, "PyPDFLoader", FakeLoader)
    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=FakeReader))
    monkeypatch.setitem(sys.modules, "PIL", types.SimpleNamespace(Image=FakePILImage))

    calls = {"n": 0}

    def fake_ocr(_img):
        calls["n"] += 1
        return f"text-{calls['n']}"

    monkeypatch.setattr(dc, "_ocr_page_image", fake_ocr)

    pages = dc.load_pdf_with_pages("dummy.pdf")
    assert pages[0].page_content == "text-1\n\ntext-2"


@pytest.mark.asyncio
async def test_sync_deleted_file_uses_file_path_for_vector_cleanup(monkeypatch, tmp_path):
    # Build a registry entry whose path is missing from disk, forcing delete flow.
    missing_path = str(tmp_path / "sub" / "doc.pdf")
    record = types.SimpleNamespace(
        file_path=missing_path,
        file_name="doc.pdf",
        content_hash="h1",
        folder_name="sub",
        is_processed=True,
    )

    monkeypatch.setattr(hr, "get_all_hashes", lambda: [record])
    monkeypatch.setattr(hr, "get_unprocessed_files", lambda: [])
    monkeypatch.setattr(hr, "remove_hash", lambda _h: True)
    monkeypatch.setattr(hr, "calculate_hash_from_file", lambda _p: "new-hash")

    from app.vectorstore import operations as ops

    captured = {"arg": None}

    def fake_delete_documents_by_file_path(path: str) -> int:
        captured["arg"] = path
        return 3

    monkeypatch.setattr(ops, "delete_documents_by_file_path", fake_delete_documents_by_file_path)
    # Keep add_documents available but no-op to avoid unrelated failures.
    monkeypatch.setattr(ops, "add_documents", lambda _docs: None)

    result = await hr.sync_data_folder_changes(tmp_path)
    assert result["deleted_files_removed"] == 1
    assert result["chunks_removed"] == 3
    assert captured["arg"] == missing_path
