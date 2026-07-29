import os
from pathlib import Path

import fitz


pdf_path = Path(os.environ.get("PDF_PATH", Path(__file__).resolve().parent.parent / "contact-branches-report.pdf"))
document = fitz.open(pdf_path)
text = "\n".join(page.get_text() for page in document).upper()

expected_pages = int(os.environ.get("EXPECTED_PDF_PAGES", "25"))
assert document.page_count == expected_pages, f"Expected {expected_pages} pages, found {document.page_count}"
for section in range(1, 12):
    assert f"SECTION {section}" in text, f"Section {section} is missing from the PDF"
