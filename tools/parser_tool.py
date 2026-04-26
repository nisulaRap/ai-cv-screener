from pathlib import Path
from typing import List, Dict, Any
import PyPDF2
from docx import Document


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from a CV file. Supports TXT, PDF, and DOCX.

    Args:
        file_path: Path to the CV file.

    Returns:
        Extracted text from the CV.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file type is unsupported or content is empty.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = path.suffix.lower()

    if extension == ".txt":
        text = path.read_text(encoding="utf-8")

    elif extension == ".pdf":
        text = ""
        with open(path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""

    elif extension == ".docx":
        doc = Document(path)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)

    else:
        raise ValueError("Unsupported file format. Use TXT, PDF, or DOCX.")

    text = text.strip()

    if not text:
        raise ValueError(f"No text could be extracted from {file_path}")

    return text


def read_all_cvs(folder_path: str = "data/cvs") -> List[Dict[str, Any]]:
    """
    Read all CV files from a folder and return extracted text.

    Args:
        folder_path: Folder containing CV files.

    Returns:
        A list of dictionaries containing file name and extracted text.
    """
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    cv_files = list(folder.glob("*.txt")) + list(folder.glob("*.pdf")) + list(folder.glob("*.docx"))

    if not cv_files:
        raise ValueError("No CV files found. Add TXT, PDF, or DOCX files to data/cvs.")

    extracted_cvs = []

    for cv_file in cv_files:
        text = extract_text_from_file(str(cv_file))
        extracted_cvs.append({
            "file_name": cv_file.name,
            "text": text
        })

    return extracted_cvs