# -*- coding: utf-8 -*-
################################################################################
# docshare/_inherit.py
#
# The generalized documentation inheritance engine.

"""Composition of documentation from one or more sources.

Inheritance in `docshare` fills gaps. Whatever the target documents for
itself is kept; a source supplies documentation only where the target has
none. Everything the decorator offers --- parameters, returns, raises, and
the rest --- is one mechanism applied to different sections, and the section
registry supplies the differences: whether a section holds items or prose,
and how its items are identified.

Two directions are at work, and the difference is not arbitrary. A
name-identified section such as Parameters is filled by *pulling*: the target
decides which parameters exist, and each is looked up in the sources. An
index-identified section such as Returns is filled by *pushing*: the target
has no list of return values to drive the process, so the source's items are
taken in order and the target's replace those it claims.
"""

from __future__ import annotations

from typing import NamedTuple

from ._cache import docinfo
from ._exceptions import DocInheritanceError, DocMappingError
from ._model import Document, FrozenDict, Section
from ._sections import (
    IDENTITY_NAME,
    IDENTITY_NAME_OR_INDEX,
    IDENTITY_TYPE_OR_INDEX,
    section_kind,
)
from ._signature import (
    PARAMETER_KINDS,
    as_names,
    signature_of,
    strip_stars,
)

__all__ = ('Operation', 'compose')


class Operation(NamedTuple):
    """One requested inheritance of one section.

    Attributes
    ----------
    kind : str or None
        The normalized section kind to inherit, or ``None`` for an opaque
        section identified by `name` instead.
    name : str or None
        The title of the opaque section to inherit, when `kind` is ``None``.
    sources : tuple
        The sources, in increasing order of precedence, so that the
        right-most wins. An entry may be a source object, or a
        ``(source, key)`` pair binding one item to one source regardless of
        that order.
    drop : frozenset
        Identities excluded from inheritance. For a section ordered by the
        target's signature these are the target's own parameter names, which
        the decorator spells ``drop<short>``; for every other section they
        are the source's item identities, spelled ``ignore<short>``.
    mapping : dict
        A correspondence from target identity to source identity.
    """

    kind: str | None = None
    name: str | None = None
    sources: tuple = ()
    drop: frozenset = frozenset()
    mapping: FrozenDict = FrozenDict()


class _Spec(NamedTuple):
    """A resolved inheritance source."""

    obj: object
    doc: Document
    key: object


def _resolve_sources(sources):
    """Resolve source specifications into documents.

    A source may be given on its own or as a ``(source, key)`` pair that
    binds one item to that source. The two are told apart by the type of the
    second element: a source is an object with documentation, never a string
    or an integer, so a pair whose second element is one of those names an
    item.
    """
    resolved = []
    for source in sources:
        key = None
        obj = source
        if isinstance(source, tuple) and len(source) == 2:
            candidate, second = source
            if isinstance(second, (str, int)) and not isinstance(second, bool):
                obj, key = candidate, second
        resolved.append(_Spec(obj=obj, doc=docinfo(obj), key=key))
    return tuple(resolved)


def _section_items(doc, kind):
    """Return every item of every section of `kind` in `doc`."""
    items = []
    for section in doc.sections:
        if section.kind == kind:
            items.extend(section.items)
    return tuple(items)


def _named_index(doc, kind):
    """Map each documented name in a section to the item declaring it."""
    index = {}
    for item in _section_items(doc, kind):
        for name in item.names:
            index.setdefault(strip_stars(name), item)
    return index


def _indexed_index(doc, kind, identity):
    """Map both the identity and the position of each item to that item."""
    index = {}
    for position, item in enumerate(_section_items(doc, kind)):
        index[position] = item
        label = _label(item, identity)
        if label is not None:
            index.setdefault(label, item)
    return index


def _label(item, identity):
    """Return an item's non-positional identity, or ``None`` if it has none."""
    if identity == IDENTITY_NAME_OR_INDEX:
        return item.names[0] if len(item.names) == 1 else None
    if identity == IDENTITY_TYPE_OR_INDEX:
        return item.type
    return None


def _lookup(specs, wanted, build_index, kind):
    """Find the item a source provides for `wanted`.

    Sources are consulted right to left, so the right-most wins, except that
    a source bound to this identity by a ``(source, key)`` pair takes
    precedence over all of them.
    """
    for spec in specs:
        if spec.key is None or not _same(spec.key, wanted):
            continue
        found = build_index(spec.doc).get(strip_stars(str(spec.key)))
        if found is None:
            raise DocMappingError(
                f'{spec.key!r} was bound to a specific source, but that '
                f'source does not document it in its {kind} section'
            )
        return found
    for spec in reversed(specs):
        if spec.key is not None:
            continue
        found = build_index(spec.doc).get(wanted)
        if found is not None:
            return found
    return None


def _same(key, wanted):
    """Compare a bound source key with a wanted identity by name."""
    return isinstance(key, str) and strip_stars(key) == strip_stars(wanted)


def _parameter_order(obj, doc, kind, extraparam, specs, mapping):
    """Decide the order the items of a name-identified section appear in.

    Every section that documents a callable's parameters is ordered by that
    callable's signature, which is what specification section 37 asks for,
    and which also settles what may be inherited: a source parameter the
    target does not accept is not a candidate at all.

    A section such as Attributes documents no parameters and has no
    signature to consult. There the target cannot say what exists, so the
    source does: the target's own names come first and the source's follow.
    A name the caller has mapped is a candidate too, since mapping it is an
    assertion that the target has it, and the source name it maps from is
    then not a candidate in its own right.
    """
    order = []
    signature = signature_of(obj) if kind in PARAMETER_KINDS else None
    if signature is not None:
        order.extend(signature.parameters)
    order.extend(strip_stars(name) for name in as_names(extraparam))
    for item in _section_items(doc, kind):
        order.extend(strip_stars(name) for name in item.names)
    if signature is None:
        order.extend(mapping)
        renamed = set(mapping.values())
        for spec in specs:
            for item in _section_items(spec.doc, kind):
                order.extend(
                    strip_stars(name)
                    for name in item.names
                    if strip_stars(name) not in renamed
                )
    seen = set()
    unique = []
    for name in order:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def _inherit_named(obj, doc, operation, kind, extraparam):
    """Compose a section whose items are identified by name."""
    specs = _resolve_sources(operation.sources)
    mapping = {
        strip_stars(str(k)): strip_stars(str(v))
        for (k, v) in dict(operation.mapping).items()
    }
    reverse = {}
    for target, source in mapping.items():
        reverse.setdefault(source, target)
    drop = {strip_stars(str(name)) for name in operation.drop}
    documented = _named_index(doc, kind)
    order = _parameter_order(obj, doc, kind, extraparam, specs, mapping)
    wanted = {
        name for name in order if name not in documented and name not in drop
    }

    def index_for(source_doc):
        return _named_index(source_doc, kind)

    emitted = []
    claimed = set()
    for name in order:
        if name in claimed:
            continue
        own = documented.get(name)
        if own is not None:
            emitted.append(own)
            claimed.update(strip_stars(n) for n in own.names)
            continue
        if name not in wanted:
            continue
        found = _lookup(specs, mapping.get(name, name), index_for, kind)
        if found is None:
            continue
        names = _group_target_names(
            found, name, reverse, wanted, documented, drop, kind, obj
        )
        emitted.append(found.evolve(names=names))
        claimed.update(strip_stars(n) for n in names)
    return tuple(emitted)


def _group_target_names(
    item, name, reverse, wanted, documented, drop, kind, obj
):
    """Translate a source item's names into the target's, keeping groups.

    A source item may document several names at once. Such a group is
    inherited whole or not at all: taking part of it would either document a
    parameter the target does not have, or contradict documentation the
    target wrote for itself. Renaming through a mapping is fine so long as
    every member of the group still corresponds to a target parameter, which
    is what keeps the group intact.
    """
    if len(item.names) <= 1:
        return (name,)
    translated = []
    missing = []
    overridden = []
    dropped = []
    for source_name in item.names:
        source_name = strip_stars(source_name)
        target_name = reverse.get(source_name, source_name)
        translated.append(target_name)
        if target_name in documented:
            overridden.append(target_name)
        elif target_name in drop:
            dropped.append(target_name)
        elif target_name not in wanted:
            missing.append(target_name)
    if not (missing or overridden or dropped):
        return tuple(translated)
    raise DocInheritanceError(
        _group_message(
            obj, kind, item, translated, missing, overridden, dropped
        )
    )


def _group_message(obj, kind, item, translated, missing, overridden, dropped):
    """Explain why a grouped declaration cannot be partially inherited."""
    name = getattr(obj, '__qualname__', None) or repr(obj)
    group = ', '.join(item.names)
    reasons = []
    if overridden:
        reasons.append(
            f'{_join(overridden)} already documented by {name} itself'
        )
    if missing:
        reasons.append(f'{_join(missing)} not a parameter of {name}')
    if dropped:
        reasons.append(f'{_join(dropped)} excluded from inheritance')
    became = ', '.join(translated)
    rename = '' if became == group else f' (which here would become {became})'
    return (
        f'the source documents {group!r} as one grouped declaration{rename}, '
        f'but only part of that group can be inherited by {name}: '
        f'{"; ".join(reasons)}. A group is inherited whole or not at all, so '
        f'either document every name in it on {name}, or document none of '
        f'them and let the whole group be inherited'
    )


def _join(names):
    """Join names for an error message."""
    quoted = [repr(name) for name in names]
    if len(quoted) == 1:
        return f'{quoted[0]} is'
    return f'{", ".join(quoted[:-1])} and {quoted[-1]} are'


def _inherit_indexed(obj, doc, operation, kind, identity):
    """Compose a section whose items are identified by position or label."""
    specs = _resolve_sources(operation.sources)
    mapping = dict(operation.mapping)
    own = _section_items(doc, kind)
    inherited = []
    for spec in specs:
        if spec.key is not None:
            continue
        inherited = list(_section_items(spec.doc, kind)) or inherited
    for spec in specs:
        if spec.key is None:
            continue
        index = _indexed_index(spec.doc, kind, identity)
        found = index.get(spec.key)
        if found is None:
            raise DocMappingError(
                f'the source bound to item {spec.key!r} does not document '
                f'it in its {kind} section'
            )
        position = _position(inherited, spec.key, identity)
        if position is None:
            inherited.append(found)
        else:
            inherited[position] = found
    keep = []
    for position, item in enumerate(inherited):
        label = _label(item, identity)
        if position in operation.drop or (
            label is not None and label in operation.drop
        ):
            continue
        keep.append(item)
    if not keep:
        return own
    return tuple(_substitute(obj, kind, keep, own, mapping, identity))


def _position(items, key, identity):
    """Return the position of `key` within `items`, or ``None``."""
    if isinstance(key, int) and not isinstance(key, bool):
        return key if 0 <= key < len(items) else None
    for position, item in enumerate(items):
        if _label(item, identity) == key:
            return position
    return None


def _substitute(obj, kind, inherited, own, mapping, identity):
    """Replace inherited items with the target's own where they correspond."""
    result = list(inherited)
    used = set()
    for position, item in enumerate(own):
        target_label = _label(item, identity)
        source_key = None
        if position in mapping:
            source_key = mapping[position]
        elif target_label is not None and target_label in mapping:
            source_key = mapping[target_label]
        elif target_label is not None:
            source_key = target_label
        if source_key is None:
            raise DocInheritanceError(
                f'{getattr(obj, "__qualname__", obj)!r} documents an '
                f'unnamed item at position {position} of its {kind} '
                f'section while inheriting that section, so there is no way '
                f'to tell which inherited item it replaces. Give the '
                f'correspondence explicitly, as in '
                f'{kind.rstrip("s")}map={{{position}: <source position>}}'
            )
        slot = _position(result, source_key, identity)
        if slot is None:
            result.append(item)
        else:
            result[slot] = item
            used.add(slot)
    return result


def _inherit_prose(doc, operation, kind):
    """Take a prose section whole, and only when the target lacks one."""
    for section in doc.sections:
        if section.kind == kind:
            return None
    specs = _resolve_sources(operation.sources)
    for spec in reversed(specs):
        for section in spec.doc.sections:
            if section.kind == kind:
                return section
    return None


def _inherit_opaque(doc, operation):
    """Take an opaque section whole, and only when the target lacks one."""
    wanted = operation.name.strip().lower()
    for section in doc.sections:
        if section.opaque and section.name.strip().lower() == wanted:
            return None
    specs = _resolve_sources(operation.sources)
    for spec in reversed(specs):
        for section in spec.doc.sections:
            if section.opaque and section.name.strip().lower() == wanted:
                return section
    return None


def compose(obj, doc, operations, *, extraparam=None):
    """Compose a document from its own documentation and its sources.

    Parameters
    ----------
    obj : object
        The object being documented, whose signature orders its parameters.
    doc : Document
        The target's own documentation, which always takes precedence.
    operations : sequence of Operation
        The inheritance to perform, in the order the sections should be
        added when the target has none.
    extraparam : str or iterable of str, optional
        Parameters that are documented deliberately although the signature
        does not name them; these participate in inheritance like any other.

    Returns
    -------
    Document
        The composed document. The target's summary and description are
        never replaced, per specification section 31.

    Raises
    ------
    DocInheritanceError
        If only part of a grouped declaration can be inherited, or if an
        unnamed item's correspondence cannot be determined.
    DocMappingError
        If a bound source does not document the item it was bound to.
    """
    sections = list(doc.sections)
    for operation in operations:
        if operation.kind is None:
            section = _inherit_opaque(doc, operation)
            if section is not None:
                sections.append(section)
            continue
        kind = section_kind(operation.kind)
        if not kind.structured:
            section = _inherit_prose(doc, operation, kind.name)
            if section is not None:
                sections.append(section)
            continue
        if kind.identity == IDENTITY_NAME:
            items = _inherit_named(obj, doc, operation, kind.name, extraparam)
        else:
            items = _inherit_indexed(
                obj, doc, operation, kind.name, kind.identity
            )
        sections = _replace_items(sections, kind, items, doc)
    return doc.evolve(sections=tuple(sections))


def _replace_items(sections, kind, items, doc):
    """Put composed items into the target's section, creating it if needed."""
    if not items:
        return sections
    result = []
    placed = False
    for section in sections:
        if section.kind == kind.name and not placed:
            result.append(section.evolve(items=items))
            placed = True
        elif section.kind == kind.name:
            continue
        else:
            result.append(section)
    if not placed:
        title = kind.titles.get(doc.format or 'numpy', kind.name)
        result.append(Section(name=title, kind=kind.name, items=items))
    return result
