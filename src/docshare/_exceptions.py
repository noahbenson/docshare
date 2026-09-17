# -*- coding: utf-8 -*-
################################################################################
# docshare/_exceptions.py
#
# The exception hierarchy used throughout docshare.

"""Exception types raised by `docshare`.

All exceptions raised deliberately by `docshare` derive from `DocShareError`,
so a single `except docshare.DocShareError` clause suffices to catch any
documentation-composition failure.
"""

__all__ = (
    'DocFormatError',
    'DocInheritanceError',
    'DocMappingError',
    'DocParseError',
    'DocShareError',
    'DocSignatureError',
)


class DocShareError(Exception):
    """Base class for all errors raised deliberately by `docshare`."""


class DocParseError(DocShareError):
    """Raised when a docstring cannot be parsed in the requested format."""


class DocFormatError(DocShareError):
    """Raised for an invalid, unsupported, or ambiguous documentation format.

    This covers a document that does not conform to an explicitly requested
    format, a document whose format cannot be detected unambiguously, and a
    composition that must render a document for which no format is known.
    """


class DocInheritanceError(DocShareError):
    """Raised when a requested inheritance operation is incoherent.

    This covers partial replacement of a grouped documentation item and
    inherited items that cannot be assigned a deterministic position in the
    target document.
    """


class DocMappingError(DocShareError):
    """Raised when an item mapping is invalid.

    The `parammap` and `returnmap` options, along with the corresponding
    mappings for other structured sections, raise this when a mapping is
    malformed or refers to items that do not exist.
    """


class DocSignatureError(DocShareError):
    """Raised when documented parameters disagree with a callable signature."""
