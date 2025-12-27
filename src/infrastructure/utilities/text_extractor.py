"""
Text extraction utilities for processing PDF and other documents

Provides robust text extraction with proper error handling and resource management.
"""

import io
import logging

import pypdfium2 as pdfium

from src.application.exceptions import PDFProcessingError, TextExtractionError


logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text content from a PDF file

    Args:
        file_content: PDF file content as bytes

    Returns:
        Extracted text from all pages

    Raises:
        PDFProcessingError: If PDF cannot be processed
        TextExtractionError: If text extraction fails
    """
    if not file_content:
        raise PDFProcessingError("Empty PDF content provided", {"content_size": 0})

    pdf_file = io.BytesIO(file_content)
    pdf_document = None
    extracted_pages: list[str] = []

    try:
        pdf_document = pdfium.PdfDocument(pdf_file, autoclose=True)

        if len(pdf_document) == 0:
            raise PDFProcessingError("PDF document has no pages", {"page_count": 0})

        logger.info(f"Processing PDF with {len(pdf_document)} pages")

        for page_num, page in enumerate(pdf_document):
            text_page = None
            try:
                text_page = page.get_textpage()
                page_text: str = text_page.get_text_bounded()  # type: ignore[no-untyped-call]
                extracted_pages.append(page_text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                # Continue with other pages
            finally:
                if text_page:
                    text_page.close()
                page.close()

        if not extracted_pages:
            raise TextExtractionError(
                "No text could be extracted from any page",
                {"page_count": len(pdf_document)},
            )

        return "\n".join(extracted_pages)

    except pdfium.PdfiumError as e:
        logger.error(f"PDF processing error: {e}")
        raise PDFProcessingError(
            "Failed to process PDF document", {"error": str(e)}
        ) from e
    except (PDFProcessingError, TextExtractionError):
        # Re-raise our own exceptions without wrapping
        raise
    except Exception as e:
        logger.error(f"Unexpected error during text extraction: {e}")
        raise TextExtractionError(
            "Failed to extract text from PDF", {"error": str(e)}
        ) from e
    finally:
        if pdf_document:
            pdf_document.close()


def extract_text_from_file(file_path: str) -> str:
    """Extract text from a file on disk

    Args:
        file_path: Path to the file

    Returns:
        Extracted text content

    Raises:
        FileNotFoundError: If file doesn't exist
        PDFProcessingError: If PDF processing fails
        TextExtractionError: If extraction fails
    """
    import os

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        # Currently only supports PDF
        if file_path.lower().endswith(".pdf"):
            return extract_text_from_pdf(content)
        else:
            raise TextExtractionError(
                "Unsupported file format",
                {"file_path": file_path, "extension": os.path.splitext(file_path)[1]},
            )
    except Exception as e:
        if isinstance(e, PDFProcessingError | TextExtractionError):
            raise
        logger.error(f"Failed to read file: {e}")
        raise TextExtractionError(
            f"Failed to extract text from file: {file_path}", {"error": str(e)}
        ) from e
