# Final Fix Report

## Changes

- `analysis.py`: require all four daily measure headers and list missing headers in a `ValueError`.
- `analysis.py`: skip all-empty daily subtotal rows while preserving rows containing explicit numeric zero.
- `index.html`: restore the Section 9 heading and set the daily chart panel title.
- `tests/test_monthly_summaries.py`: add missing-header and empty-versus-zero subtotal regression tests.
- `tests/verify-seller-daily.js`: assert both Section 9 heading levels.

No generated data or unrelated files were changed.

## TDD Evidence

- Focused Python tests before implementation: 3 failed for the expected partial-header, missing-header-row, and empty-subtotal behaviors.
- Browser test before implementation: failed because the required Section 9 heading was absent.
- Focused Python tests after implementation: 3 passed.
- Focused browser test after implementation: passed.
- Full `npm test`: passed, including 40 Python tests and all 4 browser verification scripts.
- `git diff --check`: passed.
