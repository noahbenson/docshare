# -*- coding: utf-8 -*-
################################################################################
# docshare/_lex.py
#
# Splitting a raw docstring into its summary, description, and sections.

"""The format-independent structural layer of the parser.

Before either supported format is interpreted, a docstring is split into its
summary, its description, and an ordered sequence of sections. Only the
*boundaries* are found here: the body of each section is handed on verbatim,
so that a section `docshare` does not understand can still be preserved
exactly, as required by specification sections 13 and 30.

Both supported formats are recognized at once, which is what makes automatic
format detection possible: a document that uses NumPy underlines is NumPy, a
document that uses Google headers is Google, and a document that uses both is
ambiguous and is rejected rather than guessed at.
"""

from __future__ import annotations

import inspect
import re
import textwrap
from dataclasses import dataclass

from ._exceptions import DocFormatError
from ._sections import SUPPORTED_FORMATS, section_kind

__all__ = (
    'LexedDoc',
    'LexedSection',
    'clean',
    'detect_format',
    'is_declaration',
    'is_sentence',
    'iter_blocks',
    'lex',
    'split_prose',
)


# A NumPy section header is a title on its own line, underlined with dashes:
#
#     Parameters
#     ----------
#
_NUMPY_TITLE = re.compile(r'^([A-Za-z][A-Za-z0-9 \-]*?)[ \t]*$')
_NUMPY_UNDERLINE = re.compile(r'^-{3,}[ \t]*$')

# A Google section header is a title followed by a colon, with an indented
# body beneath it:
#
#     Args:
#         x (float): The x.
#
_GOOGLE_TITLE = re.compile(r'^([A-Za-z][A-Za-z0-9 \-]*?)[ \t]*:[ \t]*$')

# A documented name is a Python identifier, optionally starred for a variadic
# parameter. Several may be declared at once, separated by commas.
_DECLARED_NAME = re.compile(r'^\*{0,2}[A-Za-z_][A-Za-z0-9_]*$')


@dataclass(frozen=True, slots=True)
class LexedSection:
    """One section of a docstring, before its body has been interpreted.

    Attributes
    ----------
    name : str
        The section title as written, without its underline or colon.
    style : str
        The header style this section was written with, either ``'numpy'``
        or ``'google'``.
    body : tuple of str
        The lines of the section body, with common indentation removed.
    """

    name: str
    style: str
    body: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LexedDoc:
    """A docstring split into its summary, description, and sections.

    Attributes
    ----------
    summary : str or None
        The opening paragraph of the document, if there is one.
    description : tuple of str
        The lines between the summary and the first section.
    sections : tuple of LexedSection
        The document's sections, in the order they appear.
    styles : frozenset of str
        The header styles that were observed. This is empty for a document
        with no sections, which belongs to neither format.
    """

    summary: str | None
    description: tuple[str, ...]
    sections: tuple[LexedSection, ...]
    styles: frozenset


def clean(text):
    """Normalize a raw docstring into a list of lines.

    Leading and trailing blank lines are removed and the uniform indentation
    that Python source gives a docstring is stripped, so that the document
    body begins at column zero.

    Parameters
    ----------
    text : str or None
        The raw documentation, typically an object's ``__doc__``.

    Returns
    -------
    list of str
        The cleaned lines. This is empty when `text` is ``None`` or blank.
    """
    if text is None:
        return []
    text = inspect.cleandoc(str(text))
    if not text.strip():
        return []
    return text.split('\n')


def _dedent(lines):
    """Remove the common leading indentation from a block of lines."""
    if not lines:
        return ()
    return tuple(textwrap.dedent('\n'.join(lines)).split('\n'))


def _trim_blank(lines):
    """Drop leading and trailing blank lines from a block of lines."""
    start = 0
    stop = len(lines)
    while start < stop and not lines[start].strip():
        start += 1
    while stop > start and not lines[stop - 1].strip():
        stop -= 1
    return lines[start:stop]


def _next_content_indent(lines, start):
    """Return the indentation of the next nonblank line, or ``None``."""
    for line in lines[start:]:
        if line.strip():
            return len(line) - len(line.lstrip())
    return None


def _numpy_header_at(lines, index):
    """Return ``(name, body_start)`` if a NumPy header begins at `index`.

    A NumPy header is unambiguous, because no item declaration is followed by
    a line of dashes.
    """
    line = lines[index]
    if not line.strip() or line[:1].isspace():
        return None
    match = _NUMPY_TITLE.match(line)
    if match is None or index + 1 >= len(lines):
        return None
    if not _NUMPY_UNDERLINE.match(lines[index + 1]):
        return None
    return (match.group(1).strip(), index + 2)


def _google_header_at(lines, index):
    """Return ``(name, body_start)`` if a Google header begins at `index`."""
    line = lines[index]
    if not line.strip() or line[:1].isspace():
        return None
    match = _GOOGLE_TITLE.match(line)
    if match is None:
        return None
    indent = _next_content_indent(lines, index + 1)
    if indent is None or indent <= 0:
        return None
    return (match.group(1).strip(), index + 1)


def _scan_numpy(lines):
    """Find every NumPy section header, as ``(index, name, body_start)``."""
    found = []
    index = 0
    while index < len(lines):
        header = _numpy_header_at(lines, index)
        if header is None:
            index += 1
            continue
        name, body_start = header
        found.append((index, name, body_start))
        index = body_start
    return found


def _scan_google(lines, first_numpy):
    """Find every Google section header, as ``(index, name, body_start)``.

    A NumPy item declaration with an empty type, such as ``x :``, has exactly
    the shape of a Google header: a title, a colon, and an indented body
    beneath it. Context tells the two apart. In a document with no NumPy
    headers at all, every candidate is a header, so that an unrecognized
    Google section is still preserved. In a document that does have NumPy
    headers, a candidate that follows the first of them is a header only if
    its title names a section `docshare` recognizes; otherwise it is an item
    declaration inside a NumPy section body.

    Parameters
    ----------
    lines : list of str
        The cleaned document lines.
    first_numpy : int or None
        The line index of the first NumPy header, or ``None`` if the
        document has none.
    """
    found = []
    index = 0
    while index < len(lines):
        header = _google_header_at(lines, index)
        if header is None:
            index += 1
            continue
        name, body_start = header
        inside_numpy = first_numpy is not None and index > first_numpy
        if inside_numpy and section_kind(name) is None:
            index += 1
            continue
        found.append((index, name, body_start))
        index = body_start
    return found


def lex(text, styles=None):
    """Split a docstring into its summary, description, and sections.

    Parameters
    ----------
    text : str or None
        The raw documentation, typically an object's ``__doc__``.
    styles : sequence of str, optional
        The header styles to recognize. The default recognizes both, which
        is what makes format detection possible. Restricting this to one
        style reads the document as that format alone, so that a construct
        which is a section header in one format and an item declaration in
        the other is read the way that format intends.

    Returns
    -------
    LexedDoc
        The structural decomposition of the document. A document with no
        sections yields an empty `LexedDoc.styles`, because such a document
        is equally valid in either supported format.
    """
    lines = clean(text)
    allowed = SUPPORTED_FORMATS if styles is None else tuple(styles)
    numpy_found = _scan_numpy(lines) if 'numpy' in allowed else []
    if 'google' in allowed:
        first = numpy_found[0][0] if numpy_found else None
        google_found = _scan_google(lines, first)
    else:
        google_found = []
    headers = sorted(
        [(i, n, 'numpy', b) for (i, n, b) in numpy_found]
        + [(i, n, 'google', b) for (i, n, b) in google_found]
    )
    preamble = lines[: headers[0][0]] if headers else lines
    sections = []
    for position, (_, name, style, body_start) in enumerate(headers):
        if position + 1 < len(headers):
            body_stop = headers[position + 1][0]
        else:
            body_stop = len(lines)
        body = _dedent(_trim_blank(lines[body_start:body_stop]))
        sections.append(LexedSection(name=name, style=style, body=body))
    summary, description = _split_preamble(_trim_blank(preamble))
    return LexedDoc(
        summary=summary,
        description=description,
        sections=tuple(sections),
        styles=frozenset(s.style for s in sections),
    )


def _split_preamble(lines):
    """Split the text before the first section into summary and description.

    The summary is the opening paragraph; the description is everything that
    follows it.
    """
    if not lines:
        return (None, ())
    stop = 0
    while stop < len(lines) and lines[stop].strip():
        stop += 1
    summary = '\n'.join(lines[:stop])
    return (summary, tuple(_trim_blank(lines[stop:])))


def iter_blocks(lines):
    """Split a section body into its items' blocks.

    Within a dedented section body, a line at column zero begins a new item
    and the indented lines beneath it are that item's description. This shape
    is shared by both supported formats, which differ only in how the line at
    column zero is written.

    Parameters
    ----------
    lines : sequence of str
        The dedented lines of a section body.

    Yields
    ------
    tuple of (str, tuple of str)
        The item's opening line, followed by its description lines with
        their common indentation removed.
    """
    header = None
    body = []
    for line in lines:
        if line.strip() and not line[:1].isspace():
            if header is not None:
                yield (header, _dedent(_trim_blank(body)))
            header = line.strip()
            body = []
        elif header is not None:
            body.append(line)
    if header is not None:
        yield (header, _dedent(_trim_blank(body)))


def detect_format(lexed):
    """Determine which format a lexed document is written in.

    Parameters
    ----------
    lexed : LexedDoc
        A lexed document, as returned by `lex`.

    Returns
    -------
    str or None
        The detected format, or ``None`` when the document has no sections
        and therefore belongs to neither format. Such a document is not
        ambiguous: it carries the same meaning in both formats.

    Raises
    ------
    DocFormatError
        If the document mixes the section syntax of both formats, in which
        case no reliable choice can be made.
    """
    styles = lexed.styles
    if len(styles) == 1:
        return next(iter(styles))
    if not styles:
        return None
    numpy = ', '.join(
        repr(s.name) for s in lexed.sections if s.style == 'numpy'
    )
    google = ', '.join(
        repr(s.name) for s in lexed.sections if s.style == 'google'
    )
    raise DocFormatError(
        'cannot determine the documentation format: the document mixes '
        f'NumPy-style sections ({numpy}) with Google-style sections '
        f'({google}).{_declaration_hint(lexed)} Pass an explicit format= to '
        f'say which was intended.'
    )


def _declaration_hint(lexed):
    """Explain a Google header that is more likely a parameter declaration.

    A NumPy parameter written with an empty type, as in ``method :``, has
    exactly the shape of a Google section header, and the name of a section
    is a perfectly ordinary name for a parameter. When the suspect header
    sits inside a NumPy section rather than before one, that is the likelier
    reading, and saying so saves the reader working it out.
    """
    first_numpy = None
    for position, section in enumerate(lexed.sections):
        if section.style == 'numpy':
            first_numpy = position
            break
    if first_numpy is None:
        return ''
    suspects = [
        s.name for s in lexed.sections[first_numpy:] if s.style == 'google'
    ]
    if not suspects:
        return ''
    name = suspects[0]
    return (
        f' A parameter declared with an empty type, as in "{name} :", has '
        f'the same shape as a Google section header; if {name!r} is a '
        f'parameter, give it a type or drop the colon.'
    )


def is_declaration(line):
    """Return whether a line opens a documentation item.

    A structured section may begin with prose describing the section as a
    whole before its items start. Telling the two apart is syntactic rather
    than a guess: an item is declared either with a type, which puts a colon
    on the line, or by naming one or more parameters, which are Python
    identifiers. Ordinary prose is neither.

    Parameters
    ----------
    line : str
        A line at column zero of a section body.

    Returns
    -------
    bool
        Whether the line declares an item rather than being prose.
    """
    text = line.strip()
    if not text:
        return False
    if ':' in text:
        return True
    parts = [part.strip() for part in text.split(',')]
    return all(_DECLARED_NAME.match(part) for part in parts if part)


def split_prose(lines):
    """Split a structured section body into leading prose and its items.

    Only *leading* prose is recognized. Text after the items has the same
    shape as a description line that lost its indentation, and guessing
    between the two would be exactly the kind of ambiguity `docshare` avoids.

    Parameters
    ----------
    lines : sequence of str
        The dedented lines of a structured section body.

    Returns
    -------
    tuple of (tuple of str, tuple of str)
        The prose lines, and the remaining lines that declare the items.
    """
    for position, line in enumerate(lines):
        if not line.strip() or line[:1].isspace():
            continue
        if is_declaration(line):
            return (
                _trim_blank(tuple(lines[:position])),
                tuple(lines[position:]),
            )
        # The first line at column zero is prose, so everything up to the
        # next declaration belongs with it.
        for later, candidate in enumerate(lines[position:], position):
            if (
                candidate.strip()
                and not candidate[:1].isspace()
                and is_declaration(candidate)
            ):
                return (
                    _trim_blank(tuple(lines[:later])),
                    tuple(lines[later:]),
                )
        return (_trim_blank(tuple(lines)), ())
    return ((), tuple(lines))


def is_sentence(line):
    """Return whether a line reads as prose rather than as a type.

    In a section whose items are identified by position, a declaration with
    no name gives the item's *type*, and a type is free text: `array_like of
    float` is a perfectly good one. So a line cannot be recognized as a type
    by its shape --- an English phrase is built from the same characters, and
    ``The computed result`` tokenizes exactly like ``array_like of float``.

    What does separate them is the end of the line. A type is a noun phrase
    and never closes a sentence, while a description usually does. The test
    is therefore deliberately narrow: a line that ends a sentence is a
    description, and anything else keeps its reading as a type, so no
    documentation changes meaning unless it was punctuated as prose.

    Parameters
    ----------
    line : str
        A declaration line with no name.

    Returns
    -------
    bool
        Whether the line reads as a description rather than a type.
    """
    return line.rstrip().endswith(('.', '!', '?'))
