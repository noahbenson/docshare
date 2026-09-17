# -*- coding: utf-8 -*-
################################################################################
# docshare/_model.py
#
# The immutable semantic representation of a parsed document.

"""The semantic document model used by `docshare`.

A parsed docstring is represented by a `Document`, which holds a summary, a
description, and an ordered sequence of `Section` objects. A structured
section holds an ordered sequence of `Item` objects; an opaque section holds
its body as text.

The representation is deliberately independent of whether the document was
written in NumPy or Google style: the same documentation produces the same
model either way, and the originating format is retained only so that the
document can be rendered back into it.

Every record in this module is immutable, so that cached documents are safe
to share between objects and cannot be modified by accident.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from ._exceptions import DocFormatError
from ._sections import SUPPORTED_FORMATS, section_kind

__all__ = (
    'Document',
    'FrozenDict',
    'Item',
    'Section',
)


class FrozenDict(Mapping):
    """An immutable, hashable mapping.

    `FrozenDict` is used for the metadata attached to the records in this
    module, so that those records remain immutable and hashable as a whole.
    It behaves like an ordinary read-only mapping in every other respect.

    Parameters
    ----------
    data : mapping or iterable of tuple, optional
        The initial contents, as accepted by `dict`.
    **kwargs
        Additional entries, as accepted by `dict`.
    """

    __slots__ = ('_data', '_hash')

    def __init__(self, data=(), /, **kwargs):
        object.__setattr__(self, '_data', dict(data, **kwargs))
        object.__setattr__(self, '_hash', None)

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f'{type(self).__name__}({self._data!r})'

    def __eq__(self, other):
        if isinstance(other, Mapping):
            return dict(self._data) == dict(other)
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        cached = self._hash
        if cached is None:
            cached = hash(frozenset(self._data.items()))
            object.__setattr__(self, '_hash', cached)
        return cached


#: The metadata used when none is supplied.
_NO_META = FrozenDict()


def _as_lines(value):
    """Return `value` as a tuple of individual lines of text."""
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(value.split('\n'))
    return tuple(str(line) for line in value)


def _as_names(value):
    """Return `value` as a tuple of documentation item names."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(name) for name in value)


def _as_meta(value):
    """Return `value` as a `FrozenDict`."""
    if isinstance(value, FrozenDict):
        return value
    if value is None:
        return _NO_META
    return FrozenDict(value)


@dataclass(frozen=True, slots=True)
class Item:
    """A single structured documentation item.

    An item is one entry in a structured section: a documented parameter, a
    return value, a raised exception, and so on. An item may document more
    than one name at once, as in the NumPy declaration ``x, y : float``; such
    an item is a *group*, and `docshare` keeps it intact.

    Attributes
    ----------
    names : tuple of str
        The names this item documents. This is empty for an item that has no
        name, such as an unnamed return value.
    type : str or None
        The documented type, retained verbatim as text. `docshare` never
        interprets this as a Python type expression.
    description : tuple of str
        The lines of the item's description, with common indentation removed.
    meta : FrozenDict
        Format-specific information retained so that the item can be
        rendered faithfully.
    """

    names: tuple[str, ...] = ()
    type: str | None = None
    description: tuple[str, ...] = ()
    meta: FrozenDict = field(default=_NO_META)

    def __post_init__(self):
        object.__setattr__(self, 'names', _as_names(self.names))
        object.__setattr__(self, 'description', _as_lines(self.description))
        object.__setattr__(self, 'meta', _as_meta(self.meta))
        if self.type is not None:
            object.__setattr__(self, 'type', str(self.type))

    @property
    def grouped(self):
        """Whether this item documents more than one name (`bool`)."""
        return len(self.names) > 1

    @property
    def name(self):
        """The single name of this item (`str` or ``None``).

        This is ``None`` for an unnamed item and for a group, which has no
        single name; use `Item.names` for those.
        """
        return self.names[0] if len(self.names) == 1 else None

    def evolve(self, **changes):
        """Return a copy of this item with the given fields replaced.

        Parameters
        ----------
        **changes
            The fields to replace.

        Returns
        -------
        Item
            The updated copy.
        """
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class Section:
    """A single section of a document.

    A section whose title `docshare` recognizes has a `Section.kind` and, if
    that kind is structured, a sequence of `Item` objects. A section whose
    title is not recognized is *opaque*: its body is preserved verbatim in
    `Section.text` and is never interpreted.

    Attributes
    ----------
    name : str
        The section title as it appears in the document, such as
        ``'Parameters'``, ``'Args'``, or ``'Efferents'``.
    kind : str or None
        The normalized kind of the section, such as ``'parameters'``, or
        ``None`` if the section is opaque.
    items : tuple of Item
        The structured items of the section, in document order.
    text : tuple of str
        The section's prose. For an opaque section this is the entire body;
        for a structured section it is any text preceding the items.
    meta : FrozenDict
        Format-specific information retained for faithful rendering.
    """

    name: str
    kind: str | None = None
    items: tuple[Item, ...] = ()
    text: tuple[str, ...] = ()
    meta: FrozenDict = field(default=_NO_META)

    def __post_init__(self):
        object.__setattr__(self, 'name', str(self.name))
        object.__setattr__(self, 'items', tuple(self.items))
        object.__setattr__(self, 'text', _as_lines(self.text))
        object.__setattr__(self, 'meta', _as_meta(self.meta))
        if self.kind is not None:
            found = section_kind(self.kind)
            if found is None:
                raise DocFormatError(
                    f'unrecognized documentation section kind: '
                    f'{self.kind!r}; pass kind=None for an opaque section'
                )
            object.__setattr__(self, 'kind', found.name)
            if not found.structured and self.items:
                raise DocFormatError(
                    f'the {found.name!r} section is prose and cannot hold '
                    f'structured items'
                )
        elif self.items:
            raise DocFormatError(
                'an opaque section cannot hold structured items'
            )
        for item in self.items:
            if not isinstance(item, Item):
                raise TypeError(
                    f'section items must be Item instances, not '
                    f'{type(item).__name__}'
                )

    @property
    def opaque(self):
        """Whether this section is preserved uninterpreted (`bool`)."""
        return self.kind is None

    @property
    def structured(self):
        """Whether this section's body consists of items (`bool`)."""
        if self.kind is None:
            return False
        return section_kind(self.kind).structured

    def evolve(self, **changes):
        """Return a copy of this section with the given fields replaced.

        Parameters
        ----------
        **changes
            The fields to replace.

        Returns
        -------
        Section
            The updated copy.
        """
        return replace(self, **changes)


@dataclass(frozen=True, slots=True)
class Document:
    """The semantic representation of a parsed docstring.

    Attributes
    ----------
    summary : str or None
        The one-line summary that opens the document, if there is one.
    description : tuple of str
        The lines of descriptive prose between the summary and the first
        section.
    sections : tuple of Section
        The document's sections, in document order. Order is significant and
        is always preserved.
    format : str or None
        The format the document was parsed from, or ``None`` when no format
        is known, as for a document built entirely from inherited sections.
    meta : FrozenDict
        Format-specific information retained for faithful rendering.
    """

    summary: str | None = None
    description: tuple[str, ...] = ()
    sections: tuple[Section, ...] = ()
    format: str | None = None
    meta: FrozenDict = field(default=_NO_META)

    def __post_init__(self):
        object.__setattr__(self, 'description', _as_lines(self.description))
        object.__setattr__(self, 'sections', tuple(self.sections))
        object.__setattr__(self, 'meta', _as_meta(self.meta))
        if self.summary is not None:
            object.__setattr__(self, 'summary', str(self.summary))
        if self.format is not None and self.format not in SUPPORTED_FORMATS:
            raise DocFormatError(
                f'unsupported documentation format: {self.format!r}; '
                f'expected one of '
                f'{", ".join(map(repr, SUPPORTED_FORMATS))} or None'
            )
        for section in self.sections:
            if not isinstance(section, Section):
                raise TypeError(
                    f'document sections must be Section instances, not '
                    f'{type(section).__name__}'
                )

    @property
    def empty(self):
        """Whether the document has no documentation at all (`bool`)."""
        return not (self.summary or self.description or self.sections)

    def __bool__(self):
        return not self.empty

    def section(self, key):
        """Return the first section matching `key`, or ``None``.

        Parameters
        ----------
        key : str
            A section kind such as ``'parameters'``, or a section title such
            as ``'Parameters'``, ``'Args'``, or ``'Efferents'``. Recognized
            titles match by kind, so that a document written in either
            supported format answers to either spelling; an unrecognized
            title matches an opaque section by name, ignoring case.

        Returns
        -------
        Section or None
            The first matching section in document order, or ``None`` if the
            document has no such section.
        """
        for section in self.iter_sections(key):
            return section
        return None

    def iter_sections(self, key):
        """Iterate over every section matching `key`, in document order.

        Parameters
        ----------
        key : str
            A section kind or title, as accepted by `Document.section`.

        Yields
        ------
        Section
            Each matching section.
        """
        kind = section_kind(key)
        if kind is None:
            target = str(key).strip().lower()
            for section in self.sections:
                if section.opaque and section.name.strip().lower() == target:
                    yield section
        else:
            for section in self.sections:
                if section.kind == kind.name:
                    yield section

    def evolve(self, **changes):
        """Return a copy of this document with the given fields replaced.

        Parameters
        ----------
        **changes
            The fields to replace.

        Returns
        -------
        Document
            The updated copy.
        """
        return replace(self, **changes)
