# -*- coding: utf-8 -*-
################################################################################
# docshare/_parser.py
#
# Assembling a semantic Document from a raw docstring.

"""The parsing engine that turns a docstring into a `docshare.Document`.

This module ties together the format-independent lexer and the two
format-specific item parsers. The result is independent of which format the
document was written in: the same documentation expressed in NumPy or Google
style produces the same `Document`, apart from the section titles and the
recorded format, which are retained so that the document can be rendered back
into the style it came from.
"""

from __future__ import annotations

from . import _google, _numpy
from ._exceptions import DocFormatError
from ._lex import detect_format, lex
from ._model import Document, Section
from ._sections import SUPPORTED_FORMATS, section_kind

__all__ = ('parse_document',)


def parse_document(text, format=None):
    """Parse a docstring into its semantic representation.

    Parameters
    ----------
    text : str or None
        The raw documentation, typically an object's ``__doc__``. A value of
        ``None``, or a blank string, yields an empty document rather than an
        error, as required by specification section 7.1.
    format : str, optional
        The format the document must be written in. When this is ``None``,
        the default, the format is detected from the document itself.

    Returns
    -------
    Document
        The parsed document.

    Raises
    ------
    DocFormatError
        If `format` is unsupported, if the document does not conform to an
        explicitly requested format, or if the format cannot be detected
        because the document mixes the section syntax of both.
    DocParseError
        If a section body cannot be read as the format requires.
    """
    if format is None:
        lexed = lex(text)
        resolved = detect_format(lexed)
    else:
        if format not in SUPPORTED_FORMATS:
            raise DocFormatError(
                f'unsupported documentation format: {format!r}; expected '
                f'one of {", ".join(map(repr, SUPPORTED_FORMATS))}'
            )
        # Read the document as the requested format alone, so that a
        # construct which is a header in the other format but an item
        # declaration in this one is read the way this format intends.
        lexed = lex(text, styles=(format,))
        if not lexed.sections:
            others = tuple(f for f in SUPPORTED_FORMATS if f != format)
            alternative = lex(text, styles=others)
            if alternative.sections:
                names = ', '.join(repr(s.name) for s in alternative.sections)
                found = alternative.sections[0].style
                raise DocFormatError(
                    f'the document was required to be {format!r} but has no '
                    f'{format} sections; its section(s) {names} use {found!r} '
                    f'section syntax'
                )
        resolved = format
    sections = tuple(_build_section(section) for section in lexed.sections)
    # The signature line is kept in the metadata rather than the summary: it
    # describes the object it was written for, so it is written back out for
    # that object and is never inherited by another.
    meta = {'signature': lexed.signature} if lexed.signature else None
    return Document(
        summary=lexed.summary,
        description=lexed.description,
        sections=sections,
        format=resolved,
        meta=meta,
    )


def _build_section(lexed):
    """Build one `Section` from one lexed section."""
    kind = section_kind(lexed.name)
    if kind is None:
        # An unrecognized section is preserved verbatim and is never
        # interpreted; see specification sections 13 and 30.
        return Section(name=lexed.name, kind=None, text=lexed.body)
    if not kind.structured:
        return Section(name=lexed.name, kind=kind.name, text=lexed.body)
    if lexed.style == 'numpy':
        (text, items) = _numpy.parse_items(lexed.body, kind)
    else:
        (text, items) = _google.parse_items(lexed.body, kind, lexed.name)
    return Section(name=lexed.name, kind=kind.name, items=items, text=text)
