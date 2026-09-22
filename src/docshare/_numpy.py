# -*- coding: utf-8 -*-
################################################################################
# docshare/_numpy.py
#
# Parsing the items of a NumPy-style section body.

"""Interpretation of NumPy-style section bodies.

The structural work of finding sections is done by `docshare._lex`; this
module is concerned only with the items inside a structured section, which in
NumPy style are written as a declaration line followed by an indented
description::

    x, y : float
        Cartesian coordinates.

A declaration may name several parameters at once, as above. Such an item is
a group, and it is kept intact rather than being split into separate items.
"""

from __future__ import annotations

import re

from ._lex import is_sentence, iter_blocks, split_prose
from ._model import Item
from ._sections import IDENTITY_NAME

__all__ = ('parse_items',)


#: A declaration line, which is a name list, a colon, and a type. Both the
#: name list and the type may be absent.
_DECLARATION = re.compile(
    r'^(?P<names>[^:]*?)[ \t]*:[ \t]*(?P<type>.*?)[ \t]*$'
)


def split_names(text):
    """Split a NumPy name list into individual names.

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


def parse_items(body, kind):
    """Parse the items of a NumPy-style structured section body.

    Parameters
    ----------
    body : sequence of str
        The dedented lines of the section body.
    kind : SectionKind
        The kind of section being parsed, which decides whether a bare
        declaration names an item or gives its type.

    Returns
    -------
    tuple of (tuple of str, tuple of Item)
        Any prose introducing the section, and the parsed items in the order
        they appear.
    """
    # Only a section whose items are named can carry prose: there a line at
    # column zero is a list of identifiers, so prose is distinguishable. In
    # a section identified by position the same line is a *type*, which is
    # free text such as ``array_like of int``, and nothing tells it from
    # prose.
    if kind.identity == IDENTITY_NAME:
        (prose, rest) = split_prose(body)
    else:
        (prose, rest) = ((), tuple(body))
    items = tuple(
        _parse_item(header, description, kind)
        for (header, description) in iter_blocks(rest)
    )
    return (prose, items)


def _parse_item(header, description, kind):
    """Build a single `Item` from a declaration line and its description."""
    match = _DECLARATION.match(header)
    if match is not None and not match.group('names').strip():
        # Nothing precedes the colon, so it is not separating a name from a
        # type. A reStructuredText role such as ``:class:`ndarray``` opens
        # this way, and splitting it there would eat its leading marker.
        match = None
    if match is None:
        # No colon: the declaration is bare. In a section whose items are
        # identified by name, such as Parameters, a bare declaration names
        # the item; elsewhere, as in Returns and Raises, it gives its type.
        if kind.identity == IDENTITY_NAME:
            return Item(
                names=split_names(header),
                type=None,
                description=description,
            )
        if is_sentence(header):
            # A type never closes a sentence. This is how Google style
            # writes a return value that has a description but no type, and
            # reading it as a type is what made that conversion one-way.
            return Item(
                names=(),
                type=None,
                description=(header, *description),
            )
        return Item(names=(), type=header, description=description)
    names = split_names(match.group('names'))
    type_ = match.group('type') or None
    return Item(names=names, type=type_, description=description)
