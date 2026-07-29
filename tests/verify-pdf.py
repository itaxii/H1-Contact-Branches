from pathlib import Path

import fitz


pdf_path = Path(__file__).resolve().parent.parent / "contact-branches-report.pdf"
document = fitz.open(pdf_path)
text = "\n".join(page.get_text() for page in document).upper()

assert document.page_count == 25, f"Expected 25 pages, found {document.page_count}"
for section in range(1, 12):
    assert f"SECTION {section}" in text, f"Section {section} is missing from the PDF"
