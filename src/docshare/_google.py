# -*- coding: utf-8 -*-
################################################################################
# docshare/_google.py
#
# Parsing the items of a Google-style section body.

"""Interpretation of Google-style section bodies.

The structural work of finding sections is done by `docshare._lex`; this
module is concerned only with the items inside a structured section, which in
Google style are written on a single opening line, optionally continued by an
indented description::

    x (float): The x coordinate.
    y (float): The y coordinate.
        A description may continue on indented lines.

Google style does not conventionally group several names in one declaration,
but `docshare` accepts a comma-separated name list where one appears, so that
a group survives a conversion from NumPy style.
"""

from __future__ import annotations

import re

from ._exceptions import DocParseError
from ._lex import iter_blocks, split_prose
from ._model import Item
from ._sections import IDENTITY_NAME

__all__ = ('parse_items',)


#: An item's opening line: a name list, an optional parenthesized type, a
#: colon, and the start of the description.
_DECLARATION = re.compile(
    r'^(?P<names>[^:()]*?)[ \t]*'
    r'(?:\((?P<type>[^)]*)\))?[ \t]*'
    r':[ \t]*(?P<description>.*?)[ \t]*$'
)


def split_names(text):
    """Split a Google name list into individual names.

    Parameters
    ----------
    text : str
        The name portion of a declaration, such as ``'x, y'``.

    Returns
    -------
    tuple of str
        The individual names, in the order written.
    """
    return tuple(part.strip() for part in text.split(',') if part.strip())


def parse_items(body, kind, section=None):
    """Parse the items of a Google-style structured section body.

    Parameters
    ----------
    body : sequence of str
        The dedented lines of the section body.
    kind : SectionKind
        The kind of section being parsed, which decides whether a bare
        declaration names an item or gives its type.
    section : str, optional
        The section title, used only to make error messages specific.

    Returns
    -------
    tuple of (tuple of str, tuple of Item)
        Any prose introducing the section, and the parsed items in the order
        they appear.

    Raises
    ------
    DocParseError
        If a line in a section whose items are identified by name cannot be
        read as an item declaration.
    """
    # See the note in docshare._numpy: prose is only distinguishable in a
    # section whose items are named. A Returns section written as bare prose
    # is one unnamed item, which is the idiom Google style uses for it.
    if kind.identity == IDENTITY_NAME:
        (prose, rest) = split_prose(body)
    else:
        (prose, rest) = ((), tuple(body))
    blocks = list(iter_blocks(rest))
    if not blocks:
        return (prose, ())
    if _DECLARATION.match(blocks[0][0]) is None:
        # A Returns or Yields section may be written as bare prose, with no
        # declaration at all; that is a single unnamed item. A section whose
        # items are identified by name has no such reading.
        if kind.identity == IDENTITY_NAME:
            raise DocParseError(
                f'cannot parse the Google-style '
                f'{section or kind.name!r} section: expected an item '
                f'declaration such as "name (type): description", but found '
                f'{blocks[0][0]!r}'
            )
        return (prose, (Item(names=(), type=None, description=tuple(rest)),))
    return (
        prose,
        tuple(
            _parse_item(header, description, kind, section)
            for (header, description) in blocks
        ),
    )


def _parse_item(header, description, kind, section):
    """Build a single `Item` from an opening line and its description."""
    match = _DECLARATION.match(header)
    if match is None:
        raise DocParseError(
            f'cannot parse an item of the Google-style '
            f'{section or kind.name!r} section: expected an item '
            f'declaration such as "name (type): description", but found '
            f'{header!r}'
        )
    raw_names = match.group('names').strip()
    type_ = match.group('type')
    opening = match.group('description')
    lines = ((opening,) if opening else ()) + tuple(description)
    if type_ is None and kind.identity != IDENTITY_NAME:
        # `float: The result.` gives a type, not a name; but
        # `result (float): The result.` gives both. The raw text is kept, so
        # that a type such as `dict, optional` is not split on its comma.
        return Item(names=(), type=raw_names or None, description=lines)
    return Item(names=split_names(raw_names), type=type_, description=lines)
