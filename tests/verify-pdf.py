import os
from pathlib import Path

import fitz


pdf_path = Path(os.environ.get("PDF_PATH", Path(__file__).resolve().parent.parent / "contact-branches-report.pdf"))
document = fitz.open(pdf_path)
text = "\n".join(page.get_text() for page in document).upper()

expected_pages = int(os.environ.get("EXPECTED_PDF_PAGES", "24"))
assert document.page_count == expected_pages, f"Expected {expected_pages} pages, found {document.page_count}"
for section in range(1, 12):
    assert f"SECTION {section}" in text, f"Section {section} is missing from the PDF"
assert "BRANCHES PER DAY - LAST MONTH" in text, "The replacement Section 9 is missing from the PDF"
assert "RENEWAL PERFORMANCE" not in text, "The removed Section 9 is still present in the PDF"
