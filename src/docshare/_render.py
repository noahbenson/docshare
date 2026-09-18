# -*- coding: utf-8 -*-
################################################################################
# docshare/_render.py
#
# Rendering a semantic Document back into docstring text.

"""Rendering of a `docshare.Document` back into ordinary docstring text.

The result is an ordinary docstring: nothing about it requires `docshare` to
read it, which is the requirement of specification section 57. Section and
item order, grouped declarations, types, and opaque sections are all
preserved, so that parsing the result yields the document that was rendered,
as required by specification sections 46 and 47.

Rendering normalizes presentation: indentation, blank lines between sections,
and the spelling of a recognized section's title all take their canonical
form for the target format. It does not normalize away content.
"""

from __future__ import annotations

from typing import NamedTuple

from ._exceptions import DocFormatError
from ._sections import (
    SUPPORTED_FORMATS,
    render_kind,
    section_kind,
    section_title,
)

__all__ = ('render_document',)

#: The indentation of a Google-style section body.
_INDENT = '    '


class _Emit(NamedTuple):
    """One section as it will be written out."""

    title: str
    items: tuple
    text: tuple
    structured: bool


def render_document(doc, format=None):
    """Render a document into docstring text.

    Parameters
    ----------
    doc : Document
        The document to render.
    format : str, optional
        The format to render into. When this is ``None``, the default, the
        document's own format is used.

    Returns
    -------
    str
        The rendered documentation, suitable for assignment to ``__doc__``.

    Raises
    ------
    DocFormatError
        If the format is unsupported, or if the document has sections but
        neither `format` nor `Document.format` says how to write them.
    """
    if format is None:
        format = doc.format
    if format is not None and format not in SUPPORTED_FORMATS:
        raise DocFormatError(
            f'unsupported documentation format: {format!r}; expected one of '
            f'{", ".join(map(repr, SUPPORTED_FORMATS))}'
        )
    if format is None:
        if doc.sections:
            raise DocFormatError(
                'cannot render a document with sections when no format is '
                'known: the document has no docstring of its own to detect '
                'a format from, so say how it should be written with '
                'render= (or format=)'
            )
        # Without sections there is nothing format-specific to write.
        format = SUPPORTED_FORMATS[0]
    lines = []
    if doc.summary:
        lines.extend(doc.summary.split('\n'))
    if doc.description:
        if lines:
            lines.append('')
        lines.extend(doc.description)
    writer = _write_numpy if format == 'numpy' else _write_google
    for emit in _plan(doc, format):
        body = writer(emit)
        if not body:
            continue
        if lines:
            lines.append('')
        lines.extend(body)
    return '\n'.join(lines).rstrip()


def _plan(doc, format):
    """Decide what sections to write, merging kinds the format lacks.

    A kind that the target format has no section of its own for is folded
    into the kind that format documents such content under; Google's
    ``Keyword Args:`` folds into NumPy's ``Parameters``. Merging happens
    here rather than in the model, so that the document itself keeps the
    distinction.
    """
    plan = []
    index = {}
    for section in doc.sections:
        if section.kind is None:
            plan.append(_Emit(section.name, (), section.text, False))
            continue
        kind = section_kind(section.kind)
        target = render_kind(kind, format)
        title = section_title(target, format)
        if not kind.structured:
            plan.append(_Emit(title, (), section.text, False))
            continue
        position = index.get(target.name)
        if position is None:
            index[target.name] = len(plan)
            plan.append(_Emit(title, tuple(section.items), section.text, True))
        else:
            merged = plan[position]
            plan[position] = merged._replace(
                items=merged.items + tuple(section.items),
                text=merged.text or section.text,
            )
    return plan


def _indent(lines, prefix=_INDENT):
    """Indent nonblank lines, leaving blank lines empty."""
    return [prefix + line if line.strip() else '' for line in lines]


def _write_numpy(emit):
    """Write one section in NumPy style."""
    body = []
    if emit.structured:
        # Prose introducing the section comes before the items, separated by
        # a blank line so that it reads as prose rather than a declaration.
        if emit.text:
            body.extend(emit.text)
            if emit.items:
                body.append('')
        for item in emit.items:
            body.extend(_numpy_item(item))
    else:
        body.extend(emit.text)
    if not body:
        # A section with no content still exists; NumPy can express that.
        return [emit.title, '-' * len(emit.title)]
    return [emit.title, '-' * len(emit.title), *body]


def _write_google(emit):
    """Write one section in Google style."""
    body = []
    if emit.structured:
        if emit.text:
            body.extend(emit.text)
            if emit.items:
                body.append('')
        for item in emit.items:
            body.extend(_google_item(item))
    else:
        body.extend(emit.text)
    if not body:
        # A Google header is only a header when an indented body follows it,
        # so an empty section cannot be written in this format.
        return []
    return [f'{emit.title}:', *_indent(body)]


def _numpy_item(item):
    """Write one item in NumPy style."""
    names = ', '.join(item.names)
    description = list(item.description)
    if names and item.type:
        head = f'{names} : {item.type}'
    elif names:
        head = names
    elif item.type:
        head = item.type
    elif description:
        # An item with neither a name nor a type has nothing to put on the
        # declaration line, so its first line of description goes there.
        head = description[0]
        description = description[1:]
    else:
        return []
    return [head, *_indent(description)]


def _google_item(item):
    """Write one item in Google style."""
    names = ', '.join(item.names)
    description = list(item.description)
    if names and item.type:
        head = f'{names} ({item.type}):'
    elif names:
        head = f'{names}:'
    elif item.type:
        head = f'{item.type}:'
    else:
        # Google style writes an item with neither a name nor a type as bare
        # prose, which is how it is read back.
        return description
    first = description[0] if description else ''
    rest = description[1:]
    return [f'{head} {first}'.rstrip(), *_indent(rest)]
