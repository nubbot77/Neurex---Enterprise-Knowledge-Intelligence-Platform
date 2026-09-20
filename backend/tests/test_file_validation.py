"""File validation — Phase 6, Task 5.

Unit tests, no database and no HTTP: these are the checks that decide whether bytes
reach storage at all, and they are cheap enough to be exhaustive about.

The tests that matter are the negative ones. "A PDF is accepted" only proves the happy
path still works; "an executable named report.pdf is refused" is the property the
check exists for.
"""

from __future__ import annotations

import pytest

from api.services.document_errors import FileContentMismatch, UnsupportedFileType
from api.services.file_validation import (
    SUPPORTED_EXTENSIONS,
    check_declared_mime_type,
    check_magic_bytes,
    extension_of,
    format_for_filename,
)

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n"
DOCX = b"PK\x03\x04\x14\x00\x06\x00[Content_Types].xml"
# The DOS header every Windows executable starts with. The file this suite cares about
# most is this one wearing a document's name.
EXE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
ELF = b"\x7fELF\x02\x01\x01\x00"


# -- extensions ---------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("handbook.pdf", "pdf"),
        ("HANDBOOK.PDF", "pdf"),
        ("notes.md", "md"),
        # The case the split has to get right: only the last extension counts.
        ("invoice.pdf.exe", "exe"),
        ("archive.tar.gz", "gz"),
        ("noextension", ""),
    ],
)
def test_extension_is_the_last_one_only(filename: str, expected: str):
    assert extension_of(filename) == expected


@pytest.mark.parametrize("extension", sorted(SUPPORTED_EXTENSIONS))
def test_every_allowlisted_extension_resolves_to_a_format(extension: str):
    assert format_for_filename(f"file.{extension}") is not None


@pytest.mark.parametrize("filename", ["payload.exe", "script.sh", "image.png", "noextension"])
def test_unsupported_extensions_are_refused(filename: str):
    """An allowlist, so anything not named on it is refused — including no extension."""
    with pytest.raises(UnsupportedFileType):
        format_for_filename(filename)


# -- declared content type ----------------------------------------------------


@pytest.mark.parametrize(
    "declared",
    [None, "", "application/octet-stream", "application/pdf", "application/pdf; charset=binary"],
)
def test_a_plausible_or_absent_content_type_is_accepted(declared: str | None):
    """Generic and missing types pass: browsers send both for legitimate uploads."""
    check_declared_mime_type(format_for_filename("a.pdf"), declared)


def test_a_content_type_naming_another_format_is_refused():
    """The client's own two claims contradict each other, before the body is read."""
    with pytest.raises(FileContentMismatch):
        check_declared_mime_type(format_for_filename("a.pdf"), "image/png")


# -- magic bytes --------------------------------------------------------------


def test_a_real_pdf_passes():
    check_magic_bytes(format_for_filename("a.pdf"), PDF)


def test_a_real_docx_passes():
    check_magic_bytes(format_for_filename("a.docx"), DOCX)


@pytest.mark.parametrize("payload", [EXE, ELF], ids=["windows-exe", "linux-elf"])
@pytest.mark.parametrize("filename", ["report.pdf", "report.docx", "report.csv", "report.md"])
def test_an_executable_is_refused_whatever_it_is_named(filename: str, payload: bytes):
    """The central case. Every allowlisted extension must reject these bytes."""
    with pytest.raises(FileContentMismatch):
        check_magic_bytes(format_for_filename(filename), payload)


def test_a_docx_named_pdf_is_refused():
    """Two formats that are both legitimate are still not interchangeable."""
    with pytest.raises(FileContentMismatch):
        check_magic_bytes(format_for_filename("a.pdf"), DOCX)


def test_a_pdf_named_docx_is_refused():
    with pytest.raises(FileContentMismatch):
        check_magic_bytes(format_for_filename("a.docx"), PDF)


@pytest.mark.parametrize(
    "filename,payload",
    [
        ("notes.md", b"# Heading\n\nSome text."),
        ("rows.csv", b"name,role\nada,admin\n"),
        ("page.html", b"<!doctype html><html><body>hi</body></html>"),
        # Non-ASCII text is ordinary, and must not be mistaken for binary.
        ("notes.md", "# Überschrift\n\nDeutsch — mit Strich.".encode()),
    ],
)
def test_text_formats_accept_text(filename: str, payload: bytes):
    check_magic_bytes(format_for_filename(filename), payload)


def test_text_formats_reject_a_nul_byte():
    """NUL cannot appear in valid text and is the cheapest binary tell there is."""
    with pytest.raises(FileContentMismatch):
        check_magic_bytes(format_for_filename("rows.csv"), b"name,role\n\x00\x00binary")


def test_html_needs_a_tag_not_merely_text():
    """Otherwise .html would be the loosest entry on the list — and so the one to pick."""
    with pytest.raises(FileContentMismatch):
        check_magic_bytes(format_for_filename("page.html"), b"just some prose, no markup")


def test_a_multibyte_character_cut_by_the_chunk_boundary_is_not_binary():
    """The sniffer sees the first chunk, which can end mid-character.

    Rejecting that would make a large UTF-8 file's acceptance depend on where the
    read happened to stop — a bug that appears only above a size threshold.
    """
    payload = ("x" * 40 + "é").encode()[:-1]
    check_magic_bytes(format_for_filename("notes.md"), payload)
