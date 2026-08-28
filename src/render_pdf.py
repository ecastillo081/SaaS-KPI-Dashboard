"""Print the case-study HTML to PDF with local Chrome or Edge."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from src.settings import REPO_ROOT

PDF_PATH = REPO_ROOT / "case-study" / "SaaS_Growth_Economics_Case_Study.pdf"

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


def find_browser() -> Path:
    for path in CHROME_CANDIDATES:
        if path.exists():
            return path
    for name in ("chrome", "msedge", "google-chrome"):
        found = shutil.which(name)
        if found:
            return Path(found)
    raise FileNotFoundError(
        "Chrome or Edge is required to print the case-study PDF. "
        "Install Chrome, or print case-study HTML locally."
    )


def _set_metadata(pdf_path: Path) -> None:
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.append(reader)
    writer.add_metadata(
        {
            "/Title": "SaaS Growth Economics",
            "/Author": "Efrain Castillo",
            "/Creator": "Efrain Castillo",
            "/Producer": "Efrain Castillo",
            "/Subject": "Self-directed portfolio case study using synthetic SaaS subscription data.",
        }
    )
    tmp = pdf_path.with_suffix(".pdf.tmp")
    with tmp.open("wb") as fh:
        writer.write(fh)
    tmp.replace(pdf_path)


def html_to_pdf(html_path: Path, pdf_path: Path | None = None) -> Path:
    browser = find_browser()
    out = Path(pdf_path) if pdf_path is not None else PDF_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    uri = html_path.resolve().as_uri()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={out}",
        "--virtual-time-budget=8000",
        uri,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    if not out.exists() or out.stat().st_size < 1000:
        raise RuntimeError(f"PDF was not created at {out}")
    _set_metadata(out)
    return out
