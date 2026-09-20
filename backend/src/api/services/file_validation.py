"""File validation — Phase 6, Task 5.

Four checks, and only one of them is worth anything on its own.

The filename and the ``Content-Type`` header are strings the client chose; they are
checked first because they are free and reject the ordinary mistakes early. The size is
checked twice, once from the header and once from the bytes actually read. What makes
the set trustworthy is the fourth check: **the leading bytes of the file are read and
have to agree with the extension**. A file called ``report.pdf`` can contain anything.

Deliberately no ``python-magic``/``libmagic`` dependency. Against an allowlist of five
formats, a signature table is a few lines, has no binary to install on Windows, and
does not answer questions we never asked. The cost is that the checks here are as deep
as the first chunk — see the note on DOCX.

Formats are the ones in ``docs/plan.md`` Phase 4. Web pages are listed there too, but
fetching a URL needs SSRF defence (architecture §18) and is not an upload, so URL
ingestion is not part of this phase.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from api.services.document_errors import FileContentMismatch, UnsupportedFileType

# How much of the front of the file the sniffers get. Every signature below is
# decided within a few dozen bytes; the rest is slack for the text formats, which
# are judged on a sample rather than a magic number.
SNIFF_BYTES = 4096


def _is_pdf(head: bytes) -> bool:
    """``%PDF-`` at byte zero.

    The PDF specification permits leading junk before the header and most readers
    tolerate it, but nothing that legitimately reaches an upload form has it, so the
    strict form is used: a tolerant check here is a way to smuggle another format past
    the sniffer.
    """
    return head.startswith(b"%PDF-")


def _is_zip(head: bytes) -> bool:
    """``PK\\x03\\x04`` — a local file header, so a zip with at least one entry.

    A ``.docx`` is an OOXML package, which is a zip. This confirms the container and
    not the package: proving it is really a Word document means reading the central
    directory for ``word/document.xml``, which is at the *end* of the file and is
    therefore unavailable to a check that must decide before the upload starts.

    That is a deliberate boundary, not an oversight. The parser in Phase 8 opens the
    package for real and fails the ingestion job if it is not one — after the bytes are
    already stored, where failing is cheap and auditable. What this check has to stop
    is an executable wearing a ``.docx`` name, and it does.
    """
    return head.startswith(b"PK\x03\x04")


def _is_text(head: bytes) -> bool:
    """Decodes as UTF-8 and contains no NUL byte.

    NUL is the classic binary marker and cannot appear in valid text. The decode is
    allowed to fail *only* at the very end of the sample, where a multi-byte character
    can legitimately be cut in half by the chunk boundary.
    """
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as error:
        return error.start >= len(head) - 4
    return True


def _is_html(head: bytes) -> bool:
    """Text, and containing a tag.

    Markdown and CSV are accepted as any valid text, so HTML needs one extra bit of
    evidence or a ``.html`` file would be the loosest format on the list — and the
    loosest format is the one an attacker picks.
    """
    return _is_text(head) and b"<" in head


@dataclass(frozen=True, slots=True)
class FileFormat:
    """One entry on the allowlist."""

    name: str
    extensions: frozenset[str]
    mime_type: str
    sniff: Callable[[bytes], bool]

    # Extra MIME types a browser may send for this format. Never used to *decide* the
    # format — only to notice when the client's own claim contradicts the extension.
    accepted_mime_types: frozenset[str] = frozenset()


FORMATS: tuple[FileFormat, ...] = (
    FileFormat(
        name="pdf",
        extensions=frozenset({"pdf"}),
        mime_type="application/pdf",
        sniff=_is_pdf,
        accepted_mime_types=frozenset({"application/pdf", "application/x-pdf"}),
    ),
    FileFormat(
        name="docx",
        extensions=frozenset({"docx"}),
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        sniff=_is_zip,
        accepted_mime_types=frozenset(
            {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/zip",
            }
        ),
    ),
    FileFormat(
        name="html",
        extensions=frozenset({"html", "htm"}),
        mime_type="text/html",
        sniff=_is_html,
        accepted_mime_types=frozenset({"text/html", "text/plain"}),
    ),
    FileFormat(
        name="markdown",
        extensions=frozenset({"md", "markdown"}),
        mime_type="text/markdown",
        sniff=_is_text,
        accepted_mime_types=frozenset({"text/markdown", "text/x-markdown", "text/plain"}),
    ),
    FileFormat(
        name="csv",
        extensions=frozenset({"csv"}),
        mime_type="text/csv",
        sniff=_is_text,
        accepted_mime_types=frozenset({"text/csv", "application/csv", "text/plain"}),
    ),
)

_BY_EXTENSION: dict[str, FileFormat] = {
    extension: fmt for fmt in FORMATS for extension in fmt.extensions
}

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(_BY_EXTENSION)


def extension_of(filename: str) -> str:
    """The lowercase extension, with no dot. Empty when there is none.

    Splits on the last dot only. ``archive.tar.gz`` is ``gz``, and
    ``invoice.pdf.exe`` is ``exe`` — which is the case this has to get right.
    """
    _, dot, extension = filename.rpartition(".")
    return extension.lower().strip() if dot else ""


def format_for_filename(filename: str) -> FileFormat:
    """Resolve the declared format from the name, or refuse the upload.

    This is the allowlist gate. Anything not on it never reaches storage, and the
    caller is told which extension it rejected — they chose the name, so naming it
    back reveals nothing.
    """
    extension = extension_of(filename)
    fmt = _BY_EXTENSION.get(extension)

    if fmt is None:
        raise UnsupportedFileType(
            f"Files of type {extension or 'unknown'!r} are not supported. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
            reason="extension_not_allowed",
        )
    return fmt


def check_declared_mime_type(fmt: FileFormat, declared: str | None) -> None:
    """Reject a ``Content-Type`` that contradicts the extension.

    An absent or generic type is accepted — browsers send
    ``application/octet-stream`` for plenty of legitimate uploads, and this check is
    not the one doing the real work. A type that names a *different* format is a
    contradiction in the client's own claims and is worth refusing early, before a
    single byte of the body is read.
    """
    if not declared:
        return

    value = declared.split(";", 1)[0].strip().lower()
    if not value or value == "application/octet-stream":
        return

    if value in fmt.accepted_mime_types or value == fmt.mime_type:
        return

    raise FileContentMismatch(
        f"Content-Type {value!r} does not match a {fmt.name} file.",
        reason="declared_mime_mismatch",
    )


def check_magic_bytes(fmt: FileFormat, head: bytes) -> None:
    """The check that actually decides. Run on the first chunk, before any upload.

    Raises ``FileContentMismatch`` when the bytes are not what the name claims.
    """
    if not fmt.sniff(head):
        raise FileContentMismatch(
            f"The file does not look like a {fmt.name} file.",
            reason="magic_byte_mismatch",
        )
