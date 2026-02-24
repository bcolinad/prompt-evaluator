"""Document processing exceptions."""

from __future__ import annotations


class DocumentProcessingError(Exception):
    """Raised when document processing fails at any stage."""

    def __init__(self, message: str, *, filename: str | None = None, stage: str | None = None) -> None:
        self.filename = filename
        self.stage = stage
        super().__init__(message)


class UnsupportedFormatError(DocumentProcessingError):
    """Raised when a file type is not supported for document processing."""

    def __init__(self, extension: str, filename: str | None = None) -> None:
        self.extension = extension
        super().__init__(
            f"Unsupported file format: {extension}",
            filename=filename,
            stage="loader",
        )
