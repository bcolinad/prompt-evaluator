"""Unit tests for the local filesystem storage client."""

import pytest

from src.utils.local_storage import LocalStorageClient


@pytest.fixture()
def storage(tmp_path):
    """Create a LocalStorageClient backed by a temp directory."""
    return LocalStorageClient(storage_path=str(tmp_path))


class TestLocalStorageInit:
    def test_creates_storage_directory(self, tmp_path):
        target = tmp_path / "sub" / "dir"
        client = LocalStorageClient(storage_path=str(target))
        assert target.is_dir()
        assert client.storage_path == target


class TestUploadFile:
    @pytest.mark.asyncio()
    async def test_upload_bytes(self, storage, tmp_path):
        result = await storage.upload_file("test.bin", b"hello bytes")
        assert result["object_key"] == "test.bin"
        assert (tmp_path / "test.bin").read_bytes() == b"hello bytes"

    @pytest.mark.asyncio()
    async def test_upload_string(self, storage, tmp_path):
        result = await storage.upload_file("test.txt", "hello text")
        assert result["object_key"] == "test.txt"
        assert (tmp_path / "test.txt").read_text() == "hello text"

    @pytest.mark.asyncio()
    async def test_upload_creates_subdirectories(self, storage, tmp_path):
        await storage.upload_file("a/b/c.txt", "nested")
        assert (tmp_path / "a" / "b" / "c.txt").read_text() == "nested"

    @pytest.mark.asyncio()
    async def test_overwrite_true_replaces_file(self, storage, tmp_path):
        await storage.upload_file("f.txt", "v1")
        await storage.upload_file("f.txt", "v2", overwrite=True)
        assert (tmp_path / "f.txt").read_text() == "v2"

    @pytest.mark.asyncio()
    async def test_overwrite_false_preserves_file(self, storage, tmp_path):
        await storage.upload_file("f.txt", "v1")
        result = await storage.upload_file("f.txt", "v2", overwrite=False)
        assert (tmp_path / "f.txt").read_text() == "v1"
        assert result["object_key"] == "f.txt"


class TestDeleteFile:
    @pytest.mark.asyncio()
    async def test_delete_existing_file(self, storage, tmp_path):
        await storage.upload_file("del.txt", "data")
        assert await storage.delete_file("del.txt") is True
        assert not (tmp_path / "del.txt").exists()

    @pytest.mark.asyncio()
    async def test_delete_nonexistent_file(self, storage):
        assert await storage.delete_file("nope.txt") is False


class TestGetReadUrl:
    @pytest.mark.asyncio()
    async def test_returns_local_files_url(self, storage):
        url = await storage.get_read_url("reports/audit.html")
        assert url == "/local-files/reports/audit.html"


class TestClose:
    @pytest.mark.asyncio()
    async def test_close_is_noop(self, storage):
        await storage.close()  # should not raise
