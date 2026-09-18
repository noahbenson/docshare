# -*- coding: utf-8 -*-
################################################################################
# docshare/_sections.py
#
# The registry of documentation sections that docshare understands
# semantically, along with the format-specific titles under which they appear.

"""The registry of semantically recognized documentation sections.

`docshare` normalizes equivalent format-specific section titles onto a single
set of *kinds*, so that a NumPy ``Parameters`` section and a Google ``Args:``
section produce the same semantic representation. Sections that are not in
this registry are preserved as opaque documentation rather than being
interpreted; see the `docshare.Section` class.

Every recognized kind declares:

* whether it is *structured* --- that is, whether its body consists of
  discrete documentation items rather than prose;
* how its items are identified, for the purposes of mapping and dropping
  them during inheritance;
* the canonical title it is rendered with in each supported format;
* the kind it is merged into when a format has no section of its own for it.

The last of these exists because the formats do not recognize quite the same
sections. Google style has a ``Keyword Args:`` section; the NumPy standard
does not, and documents keyword arguments in ``Parameters`` instead. Such a
kind is kept distinct in the model, so that a document written in a format
that distinguishes it round-trips faithfully, and is merged only when it is
rendered into a format that does not.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ._exceptions import DocFormatError
from ._frozendict import FrozenDict

__all__ = (
    'IDENTITY_NAME',
    'IDENTITY_NAME_OR_INDEX',
    'IDENTITY_TYPE_OR_INDEX',
    'SUPPORTED_FORMATS',
    'TITLE_CHARACTERS',
    'SectionKind',
    'custom_kind',
    'iter_section_kinds',
    'kind_name',
    'normalize_title',
    'render_kind',
    'section_kind',
    'section_title',
)


#: The documentation formats that `docshare` can parse and render.
SUPPORTED_FORMATS = ('google', 'numpy')

#: The characters a section title may be written with. Both formats agree on
#: this, and the lexer builds its header patterns from it, so a title that
#: does not match is one no docstring can express in either format.
TITLE_CHARACTERS = r'[A-Za-z][A-Za-z0-9 \-]*?'

_TITLE = re.compile(f'^{TITLE_CHARACTERS}$')

#: Items are identified by name alone; for example, a parameter.
IDENTITY_NAME = 'name'

#: Items are identified by name when they have one and by their zero-based
#: position otherwise; for example, a return value.
IDENTITY_NAME_OR_INDEX = 'name_or_index'

#: Items are identified by their type when they have one and by their
#: zero-based position otherwise; for example, a raised exception.
IDENTITY_TYPE_OR_INDEX = 'type_or_index'


@dataclass(frozen=True, slots=True)
class SectionKind:
    """A documentation section that `docshare` understands semantically.

    Attributes
    ----------
    name : str
        The normalized name of the kind, such as ``'parameters'``.
    structured : bool
        Whether the section body consists of discrete documentation items
        rather than prose.
    identity : str or None
        How items in this section are identified during inheritance; one of
        `IDENTITY_NAME`, `IDENTITY_NAME_OR_INDEX`, or
        `IDENTITY_TYPE_OR_INDEX`. This is ``None`` for prose sections.
    titles : Mapping[str, str]
        The canonical title of this section in each supported format.
    aliases : tuple of str
        The normalized titles that map onto this kind.
    merges : Mapping[str, str]
        The kind this one is merged into when rendered in a given format,
        for formats that have no section of their own for it. Formats absent
        from this mapping render the section under its own title.
    placeholder : str or None
        The type to write when an item of this section has a description but
        no type. NumPy style requires a type for every item of a section
        identified by position, so one has to be supplied; the least
        specific type of the relevant hierarchy says no more than the author
        did. This is ``None`` for a section that needs no such type.
    """

    name: str
    structured: bool
    identity: str | None
    titles: Mapping[str, str]
    aliases: tuple[str, ...]
    merges: Mapping[str, str]
    placeholder: str | None


# Kinds that one format has no section of its own for, and the kind they are
# therefore merged into when rendered in that format. The NumPy standard has
# no keyword-argument section; keyword arguments are documented in Parameters.
_MERGES = {
    'keyword_arguments': {'numpy': 'parameters'},
}


# The type written when an item has a description but no type of its own.
# The NumPy standard requires a type for every item of these sections --- its
# specification says so of Returns and repeats it for Yields --- so one must
# be written, and the base of the relevant hierarchy asserts no more than the
# author did. Google style has no such requirement and writes no type at all,
# which is how the two round-trip within their own format.
_PLACEHOLDERS = {
    'returns': 'object',
    'yields': 'object',
    'raises': 'Exception',
    'warns': 'Warning',
}


# The registry itself. Each entry is:
#     (name, structured, identity, numpy title, google title, aliases)
_KIND_DATA = (
    (
        'parameters',
        True,
        IDENTITY_NAME,
        'Parameters',
        'Args',
        ('parameters', 'params', 'args', 'arguments'),
    ),
    (
        'other_parameters',
        True,
        IDENTITY_NAME,
        'Other Parameters',
        'Other Parameters',
        ('other parameters', 'other params', 'other args', 'other arguments'),
    ),
    (
        'keyword_arguments',
        True,
        IDENTITY_NAME,
        'Keyword Arguments',
        'Keyword Args',
        ('keyword arguments', 'keyword args'),
    ),
    (
        'returns',
        True,
        IDENTITY_NAME_OR_INDEX,
        'Returns',
        'Returns',
        ('returns', 'return'),
    ),
    (
        'yields',
        True,
        IDENTITY_NAME_OR_INDEX,
        'Yields',
        'Yields',
        ('yields', 'yield'),
    ),
    (
        'receives',
        True,
        IDENTITY_NAME,
        'Receives',
        'Receives',
        ('receives', 'receive'),
    ),
    (
        'raises',
        True,
        IDENTITY_TYPE_OR_INDEX,
        'Raises',
        'Raises',
        ('raises', 'raise', 'exceptions'),
    ),
    (
        'warns',
        True,
        IDENTITY_TYPE_OR_INDEX,
        'Warns',
        'Warns',
        ('warns', 'warn'),
    ),
    (
        'attributes',
        True,
        IDENTITY_NAME,
        'Attributes',
        'Attributes',
        ('attributes', 'attribute'),
    ),
    (
        'methods',
        True,
        IDENTITY_NAME,
        'Methods',
        'Methods',
        ('methods', 'method'),
    ),
    (
        'warnings',
        False,
        None,
        'Warnings',
        'Warnings',
        ('warnings', 'warning'),
    ),
    (
        'see_also',
        False,
        None,
        'See Also',
        'See Also',
        ('see also',),
    ),
    (
        'notes',
        False,
        None,
        'Notes',
        'Notes',
        ('notes', 'note'),
    ),
    (
        'references',
        False,
        None,
        'References',
        'References',
        ('references', 'reference'),
    ),
    (
        'examples',
        False,
        None,
        'Examples',
        'Examples',
        ('examples', 'example'),
    ),
)


def _build_registry():
    kinds = {}
    aliases = {}
    for name, structured, identity, numpy, google, alias in _KIND_DATA:
        kind = SectionKind(
            name=name,
            structured=structured,
            identity=identity,
            titles=FrozenDict({'numpy': numpy, 'google': google}),
            aliases=tuple(alias),
            merges=FrozenDict(_MERGES.get(name, {})),
            placeholder=_PLACEHOLDERS.get(name),
        )
        kinds[name] = kind
        for text in alias:
            if text in aliases:  # pragma: no cover - guards the table itself
                raise RuntimeError(f'duplicate section alias: {text}')
            aliases[text] = kind
    return MappingProxyType(kinds), MappingProxyType(aliases)


_KINDS, _ALIASES = _build_registry()


def normalize_title(title):
    """Return the normalized lookup form of a section title.

    Normalization lowercases the title, removes a trailing colon (as used by
    Google-style section headers), and collapses internal whitespace. It does
    not determine whether the resulting title is recognized.

    Parameters
    ----------
    title : str
        The section title as it appears in a docstring.

    Returns
    -------
    str
        The normalized title.
    """
    text = str(title).strip()
    if text.endswith(':'):
        text = text[:-1].strip()
    return ' '.join(text.lower().split())


def section_kind(title):
    """Return the `SectionKind` for a section title, if it is recognized.

    Parameters
    ----------
    title : str
        The section title as it appears in a docstring, or a normalized kind
        name such as ``'see_also'``.

    Returns
    -------
    SectionKind or None
        The matching kind, or ``None`` if the title is not semantically
        recognized and must therefore be treated as opaque.
    """
    text = normalize_title(title)
    kind = _ALIASES.get(text)
    if kind is not None:
        return kind
    return _KINDS.get(text.replace(' ', '_'))


def kind_name(title):
    """Return the normalized kind name that a section title produces.

    Parameters
    ----------
    title : str
        The section title as it appears in a docstring.

    Returns
    -------
    str
        The kind name, such as ``'see_also'`` for ``'See Also'``.
    """
    return normalize_title(title).replace(' ', '_')


def custom_kind(title, like):
    """Build a `SectionKind` for a section the caller has declared.

    A declared section is a kind of its own rather than another name for an
    existing one, because the two can appear in the same document and mean
    different things: a model's ``Parameters`` may be the values being
    fitted while its ``Inputs`` are the observations they are fitted to.
    Treating the second as a spelling of the first would merge them when the
    document is rendered and check both against the signature.

    What the declared section borrows from the one it resembles is how its
    body is *read*: whether it holds items, how those items are identified,
    and what type stands in for one the author left out. What it does not
    borrow is its titles, which are the spelling declared here in both
    formats; its merges, which are empty, since it has no equivalent in
    either format to be folded into; or membership of the parameter kinds,
    so that it is never checked against a signature and is inherited from
    its sources rather than from the target's parameter list.

    Parameters
    ----------
    title : str
        The section title, as it should be written in a docstring.
    like : SectionKind or str
        The recognized section this one resembles.

    Returns
    -------
    SectionKind
        The declared kind.

    Raises
    ------
    DocFormatError
        If the title is one `docshare` already recognizes, or is not one a
        docstring could express.
    """
    text = str(title).strip()
    if not _TITLE.match(text):
        raise DocFormatError(
            f'{text!r} cannot be a section title: a title is written with '
            f'letters, digits, spaces and hyphens, and begins with a letter, '
            f'in both supported formats'
        )
    if section_kind(text) is not None:
        raise DocFormatError(
            f'{text!r} is a section docshare already recognizes and cannot '
            f'be declared as a custom section'
        )
    model = like if isinstance(like, SectionKind) else section_kind(like)
    if model is None:
        raise DocFormatError(
            f'the custom section {text!r} is declared to resemble {like!r}, '
            f'which is not a section docshare recognizes'
        )
    name = kind_name(text)
    return SectionKind(
        name=name,
        structured=model.structured,
        identity=model.identity,
        titles=FrozenDict(dict.fromkeys(SUPPORTED_FORMATS, text)),
        aliases=(normalize_title(text),),
        # A declared section has no equivalent in either format, so it is
        # never merged into another; and it is not a parameter kind, so it
        # is never checked against a signature.
        merges=FrozenDict(),
        placeholder=model.placeholder,
    )


def section_title(kind, format):
    """Return the canonical title of a section kind in a given format.

    Parameters
    ----------
    kind : SectionKind or str
        The section kind, or the name of one.
    format : str
        One of the values in `SUPPORTED_FORMATS`.

    Returns
    -------
    str
        The canonical title, such as ``'Parameters'`` or ``'Args'``.

    Raises
    ------
    DocFormatError
        If the format is not supported or the kind is not recognized.
    """
    if format not in SUPPORTED_FORMATS:
        raise DocFormatError(
            f'unsupported documentation format: {format!r}; expected one of '
            f'{", ".join(map(repr, SUPPORTED_FORMATS))}'
        )
    if not isinstance(kind, SectionKind):
        found = section_kind(kind)
        if found is None:
            raise DocFormatError(
                f'unrecognized documentation section kind: {kind!r}'
            )
        kind = found
    return kind.titles[format]


def render_kind(kind, format):
    """Return the kind a section is actually rendered as in a given format.

    Most sections render as themselves. A section that the requested format
    has no equivalent of is merged into the kind that format documents such
    content under; a Google ``Keyword Args:`` section, for example, renders
    into ``Parameters`` in NumPy style, because the NumPy standard has no
    keyword-argument section.

    Parameters
    ----------
    kind : SectionKind or str
        The section kind, or the name of one.
    format : str
        One of the values in `SUPPORTED_FORMATS`.

    Returns
    -------
    SectionKind
        The kind to render under. This is `kind` itself unless the format
        requires a merge.

    Raises
    ------
    DocFormatError
        If the format is not supported or the kind is not recognized.
    """
    if format not in SUPPORTED_FORMATS:
        raise DocFormatError(
            f'unsupported documentation format: {format!r}; expected one of '
            f'{", ".join(map(repr, SUPPORTED_FORMATS))}'
        )
    if not isinstance(kind, SectionKind):
        found = section_kind(kind)
        if found is None:
            raise DocFormatError(
                f'unrecognized documentation section kind: {kind!r}'
            )
        kind = found
    target = kind.merges.get(format)
    return kind if target is None else _KINDS[target]


def iter_section_kinds():
    """Iterate over every recognized `SectionKind`, in registry order.

    Returns
    -------
    iterator of SectionKind
        An iterator over the recognized section kinds.
    """
    return iter(_KINDS.values())
