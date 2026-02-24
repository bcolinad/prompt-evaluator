"""Unit tests for the chat handler functions in app.py."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from unittest.mock import MagicMock

from src.app import _extract_chunk_deltas, _extract_thinking_and_text, _process_attachments

# ---------------------------------------------------------------------------
# _extract_thinking_and_text tests
# ---------------------------------------------------------------------------


class TestExtractThinkingAndText:
    """Tests for the thinking/text extraction helper."""

    def test_string_content(self) -> None:
        thinking, text = _extract_thinking_and_text("Hello world")
        assert thinking == ""
        assert text == "Hello world"

    def test_empty_string(self) -> None:
        thinking, text = _extract_thinking_and_text("")
        assert thinking == ""
        assert text == ""

    def test_dict_blocks_with_thinking(self) -> None:
        content = [
            {"type": "thinking", "text": "Let me think about this..."},
            {"type": "text", "text": "Here is my answer."},
        ]
        thinking, text = _extract_thinking_and_text(content)
        assert thinking == "Let me think about this..."
        assert text == "Here is my answer."

    def test_dict_blocks_no_thinking(self) -> None:
        content = [
            {"type": "text", "text": "Direct answer."},
        ]
        thinking, text = _extract_thinking_and_text(content)
        assert thinking == ""
        assert text == "Direct answer."

    def test_typed_objects_with_thinking(self) -> None:
        @dataclass
        class Block:
            type: str
            text: str

        content = [
            Block(type="thinking", text="Reasoning here"),
            Block(type="text", text="Final response"),
        ]
        thinking, text = _extract_thinking_and_text(content)
        assert thinking == "Reasoning here"
        assert text == "Final response"

    def test_multiple_thinking_blocks(self) -> None:
        content = [
            {"type": "thinking", "text": "Step 1"},
            {"type": "thinking", "text": "Step 2"},
            {"type": "text", "text": "Answer"},
        ]
        thinking, text = _extract_thinking_and_text(content)
        assert "Step 1" in thinking
        assert "Step 2" in thinking
        assert text == "Answer"

    def test_non_list_non_string(self) -> None:
        thinking, text = _extract_thinking_and_text(42)
        assert thinking == ""
        assert text == "42"

    def test_empty_list(self) -> None:
        thinking, text = _extract_thinking_and_text([])
        assert thinking == ""
        assert text == ""

    def test_mixed_dict_and_typed_blocks(self) -> None:
        @dataclass
        class Block:
            type: str
            text: str

        content = [
            {"type": "thinking", "text": "Dict thinking"},
            Block(type="text", text="Object text"),
        ]
        thinking, text = _extract_thinking_and_text(content)
        assert thinking == "Dict thinking"
        assert text == "Object text"


# ---------------------------------------------------------------------------
# _extract_chunk_deltas tests
# ---------------------------------------------------------------------------


class TestExtractChunkDeltas:
    """Tests for the streaming chunk delta extractor."""

    def test_string_content(self) -> None:
        thinking, text = _extract_chunk_deltas("Hello")
        assert thinking == ""
        assert text == "Hello"

    def test_empty_string(self) -> None:
        thinking, text = _extract_chunk_deltas("")
        assert thinking == ""
        assert text == ""

    def test_none_content(self) -> None:
        thinking, text = _extract_chunk_deltas(None)
        assert thinking == ""
        assert text == ""

    def test_dict_thinking_block(self) -> None:
        content = [{"type": "thinking", "thinking": "Let me reason..."}]
        thinking, text = _extract_chunk_deltas(content)
        assert thinking == "Let me reason..."
        assert text == ""

    def test_dict_thinking_block_fallback_to_text_key(self) -> None:
        content = [{"type": "thinking", "text": "Fallback thinking"}]
        thinking, text = _extract_chunk_deltas(content)
        assert thinking == "Fallback thinking"
        assert text == ""

    def test_dict_text_block(self) -> None:
        content = [{"type": "text", "text": "Response text"}]
        thinking, text = _extract_chunk_deltas(content)
        assert thinking == ""
        assert text == "Response text"

    def test_typed_object_with_thinking_attr(self) -> None:
        @dataclass
        class ThinkingBlock:
            type: str
            thinking: str
            text: str = ""

        content = [ThinkingBlock(type="thinking", thinking="Deep thought")]
        thinking, text = _extract_chunk_deltas(content)
        assert thinking == "Deep thought"
        assert text == ""

    def test_typed_object_text_block(self) -> None:
        @dataclass
        class TextBlock:
            type: str
            text: str

        content = [TextBlock(type="text", text="Streamed text")]
        thinking, text = _extract_chunk_deltas(content)
        assert thinking == ""
        assert text == "Streamed text"

    def test_empty_list(self) -> None:
        thinking, text = _extract_chunk_deltas([])
        assert thinking == ""
        assert text == ""

    def test_non_list_non_string(self) -> None:
        thinking, text = _extract_chunk_deltas(42)
        assert thinking == ""
        assert text == "42"


# ---------------------------------------------------------------------------
# _process_attachments tests
# ---------------------------------------------------------------------------


class TestProcessAttachments:
    """Tests for the file attachment processor."""

    def test_text_file_reads_content(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("print('hello')")
            f.flush()
            elem = MagicMock(name="script.py", path=f.name)
            elem.name = "script.py"

        text_prefix, image_blocks, _ = _process_attachments([elem])
        assert "print('hello')" in text_prefix
        assert "```py" in text_prefix
        assert image_blocks == []

    def test_oversized_file_skipped(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            # Write more than 100KB
            f.write("x" * (101 * 1024))
            f.flush()
            elem = MagicMock(name="big.txt", path=f.name)
            elem.name = "big.txt"

        text_prefix, image_blocks, _ = _process_attachments([elem])
        assert "Skipped" in text_prefix
        assert "100KB" in text_prefix
        assert image_blocks == []

    def test_unsupported_extension_skipped(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".zip", mode="wb", delete=False) as f:
            f.write(b"PK\x03\x04")
            f.flush()
            elem = MagicMock(name="archive.zip", path=f.name)
            elem.name = "archive.zip"

        text_prefix, image_blocks, _ = _process_attachments([elem])
        assert "Skipped" in text_prefix
        assert "unsupported" in text_prefix
        assert image_blocks == []

    def test_image_file_returns_base64_block(self) -> None:
        # Create a minimal 1x1 PNG
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with tempfile.NamedTemporaryFile(suffix=".png", mode="wb", delete=False) as f:
            f.write(png_bytes)
            f.flush()
            elem = MagicMock(name="photo.png", path=f.name)
            elem.name = "photo.png"

        text_prefix, image_blocks, _ = _process_attachments([elem])
        assert text_prefix == ""
        assert len(image_blocks) == 1
        assert image_blocks[0]["type"] == "image_url"
        assert "data:image/png;base64," in image_blocks[0]["image_url"]["url"]

    def test_missing_path_skipped(self) -> None:
        elem = MagicMock(name="file.txt", path=None)
        elem.name = "file.txt"

        text_prefix, image_blocks, _ = _process_attachments([elem])
        assert text_prefix == ""
        assert image_blocks == []

    def test_empty_elements_list(self) -> None:
        text_prefix, image_blocks, _ = _process_attachments([])
        assert text_prefix == ""
        assert image_blocks == []

    def test_jpeg_extension_uses_correct_media_type(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jpg", mode="wb", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0")  # minimal JPEG header
            f.flush()
            elem = MagicMock(name="photo.jpg", path=f.name)
            elem.name = "photo.jpg"

        _, image_blocks, _ = _process_attachments([elem])
        assert len(image_blocks) == 1
        assert "data:image/jpeg;base64," in image_blocks[0]["image_url"]["url"]
