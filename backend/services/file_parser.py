"""File parser — extracts text from uploaded files.

Handles:
  - .txt, .md, .py, .kt, .java, .js, .ts → read as plain text
  - .pdf → extract with pdfplumber
  - .docx → extract with python-docx (if installed), else skip
"""
import io
import os


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Extract readable text from file bytes based on extension."""
    ext = os.path.splitext(filename)[1].lower()

    # Plain text files
    if ext in (".txt", ".md", ".py", ".kt", ".java", ".js", ".ts", ".jsx", ".tsx", ".xml", ".json", ".csv"):
        return data.decode("utf-8", errors="replace")

    # PDF
    if ext == ".pdf":
        return _parse_pdf(data)

    # DOCX
    if ext == ".docx":
        return _parse_docx(data)

    # Fallback: try as text
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _parse_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)
    except ImportError:
        return "[PDF parsing unavailable — install pdfplumber]"
    except Exception as e:
        return f"[PDF parse error: {e}]"


def _parse_docx(data: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return "[DOCX parsing unavailable — install python-docx]"
    except Exception as e:
        return f"[DOCX parse error: {e}]"
