# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "docling",
# ]
# ///
from __future__ import annotations

import json
from pathlib import Path
import shutil
from docling.document_converter import DocumentConverter

DATA_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = DATA_DIR / "downloads"
MARKDOWN_DIR = DATA_DIR / "markdown"


def convert_all():
    manifest_path = DOWNLOADS_DIR / "manifest.json"
    if not manifest_path.exists():
        print(
            f"Error: Manifest not found at {manifest_path}. Please run download script first."
        )
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Clear and recreate output directory to prevent stale/orphaned files
    if MARKDOWN_DIR.exists():
        shutil.rmtree(MARKDOWN_DIR)
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

    print("Initializing Docling DocumentConverter...")
    converter = DocumentConverter()

    markdown_manifest = {
        "source": manifest.get("source", "SEC EDGAR"),
        "generated_at_utc": manifest.get("generated_at_utc"),
        "form": manifest.get("form", "10-K"),
        "downloaded_count": 0,
        "filings": [],
    }

    filings = manifest.get("filings", [])
    total = len(filings)
    print(f"Starting conversion of {total} filings...")

    for idx, filing in enumerate(filings, 1):
        ticker = filing.get("ticker")
        year = (filing.get("report_date") or filing.get("filing_date") or "0000")[:4]
        local_html_path_str = filing.get("local_path")

        # Get local htm file path (handling windows backslash / unix slash normalization)
        html_path = DOWNLOADS_DIR / Path(local_html_path_str)
        if not html_path.exists():
            print(
                f"[{idx}/{total}] Warning: File {html_path} does not exist. Skipping."
            )
            continue

        year_dir = MARKDOWN_DIR / year
        year_dir.mkdir(parents=True, exist_ok=True)

        md_filename = html_path.with_suffix(".md").name
        md_path = year_dir / md_filename
        # Store clean path with forward slashes for cross-platform compatibility
        relative_md_path = f"{year}/{md_filename}"

        print(
            f"[{idx}/{total}] Converting {ticker} ({year}) file: {html_path.name} to {relative_md_path}..."
        )

        try:
            result = converter.convert(html_path)
            markdown_content = result.document.export_to_markdown()

            # Write markdown file
            md_path.write_text(markdown_content, encoding="utf-8")

            # Add to markdown manifest
            markdown_manifest["filings"].append(
                {
                    "ticker": filing.get("ticker"),
                    "cik": filing.get("cik"),
                    "form": filing.get("form"),
                    "filing_date": filing.get("filing_date"),
                    "report_date": filing.get("report_date"),
                    "accession_number": filing.get("accession_number"),
                    "primary_document": filing.get("primary_document"),
                    "source_url": filing.get("source_url"),
                    "local_path": relative_md_path,
                }
            )
            markdown_manifest["downloaded_count"] += 1
            print(f"[{idx}/{total}] Successfully converted {ticker} ({year}).")
        except Exception as e:
            print(f"[{idx}/{total}] Error converting {html_path.name}: {e}")

    # Write new manifest.json under markdown/ folder
    output_manifest_path = MARKDOWN_DIR / "manifest.json"
    with open(output_manifest_path, "w", encoding="utf-8") as f:
        json.dump(markdown_manifest, f, indent=2)
    print(
        f"Conversion complete! Markdown manifest saved to {output_manifest_path}"
    )


if __name__ == "__main__":
    convert_all()
