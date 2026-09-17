# -*- coding: utf-8 -*-
################################################################################
# docshare/_decorator.py
#
# The docshare decorator itself.

"""The `docshare` decorator.

The decorator is the whole library seen from the outside: it parses the
decorated object's documentation, performs the inheritance the caller asked
for, renders the result, and assigns it back. Everything it accepts is
shorthand for the generalized inheritance described in specification section
43, and the shorthand is generated from the section registry rather than
written out section by section, so that the vocabulary is uniform.

For a section named by its short form --- ``params`` for Parameters,
``seealso`` for See Also, and so on --- the decorator accepts
``inherit<short>`` for every section, and for a section that holds items also
``drop<short>`` and ``<singular>map``. So Parameters offers `inheritparams`,
`dropparams`, and `parammap`, and Raises offers `inheritraises`,
`dropraises`, and `raisemap`.

Composition happens once, when the decorator runs. Nothing is recomputed
afterwards, and a docstring assigned later by another decorator is outside
`docshare`'s control, as specification sections 34 and 35 describe.
"""

from __future__ import annotations

import difflib

from ._cache import docparse, set_docinfo
from ._exceptions import DocShareError
from ._inherit import Operation, compose
from ._render import render_document
from ._sections import iter_section_kinds, section_kind
from ._signature import validate_signature

__all__ = ('docshare',)


#: Short forms that do not follow from the kind name directly.
_SHORT_FORMS = {
    'parameters': 'params',
    'other_parameters': 'otherparams',
    'keyword_arguments': 'keywordargs',
    'see_also': 'seealso',
}


def _short(kind_name):
    """Return the short form a kind's arguments are named after."""
    return _SHORT_FORMS.get(kind_name, kind_name)


def _map_name(short):
    """Return the mapping-argument name for a short form."""
    stem = short[:-1] if short.endswith('s') else short
    return f'{stem}map'


def _build_arguments():
    """Build the table of per-section arguments the decorator accepts."""
    table = {}
    for kind in iter_section_kinds():
        short = _short(kind.name)
        table[f'inherit{short}'] = ('inherit', kind.name)
        if kind.structured:
            table[f'drop{short}'] = ('drop', kind.name)
            table[_map_name(short)] = ('map', kind.name)
    return table


#: Maps each accepted per-section argument to its role and section kind.
SECTION_ARGUMENTS = _build_arguments()

#: The arguments accepted in addition to the per-section ones.
GENERAL_ARGUMENTS = (
    'format',
    'render',
    'inherit',
    'inheritall',
    'inheritother',
    'extraparam',
)


def _is_item_key(value):
    """Return whether `value` identifies an item rather than a source.

    A source is an object with documentation and is never a string or an
    integer, so the two are unambiguous. `True` and `False` are integers to
    Python but are not positions, and are not treated as keys.
    """
    if isinstance(value, bool):
        return False
    return isinstance(value, (str, int))


def _as_source_specs(value):
    """Normalize an inheritance-source argument into a tuple of specs.

    A single source stands for itself. A sequence gives several sources, in
    increasing order of precedence. A two-element sequence whose second
    element identifies an item is one source bound to that item.
    """
    if value is None:
        return ()
    if isinstance(value, (tuple, list)):
        if len(value) == 2 and _is_item_key(value[1]):
            return (tuple(value),)
        specs = []
        for entry in value:
            if (
                isinstance(entry, (tuple, list))
                and len(entry) == 2
                and _is_item_key(entry[1])
            ):
                specs.append(tuple(entry))
            else:
                specs.append(entry)
        return tuple(specs)
    return (value,)


def _as_identities(value):
    """Normalize a drop argument into a frozenset of identities."""
    if value is None:
        return frozenset()
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        return frozenset({value})
    return frozenset(value)


def _unknown_argument(name):
    """Raise a helpful error for an argument `docshare` does not accept."""
    known = sorted(set(SECTION_ARGUMENTS) | set(GENERAL_ARGUMENTS))
    close = difflib.get_close_matches(name, known, n=3, cutoff=0.6)
    hint = f'; did you mean {" or ".join(map(repr, close))}?' if close else ''
    raise DocShareError(
        f'docshare() got an unexpected argument {name!r}{hint}'
    )


def _collect(options):
    """Sort the decorator's per-section arguments by role and kind.

    Every name is known to be valid: `_apply` rejects unrecognized arguments
    before any work is done.
    """
    inherits = {}
    drops = {}
    maps = {}
    for name, value in options.items():
        if name in GENERAL_ARGUMENTS:
            continue
        (role, kind) = SECTION_ARGUMENTS[name]
        if role == 'inherit':
            inherits[kind] = _as_source_specs(value)
        elif role == 'drop':
            drops[kind] = _as_identities(value)
        else:
            maps[kind] = dict(value or {})
    return (inherits, drops, maps)


def _from_general_inherit(value):
    """Expand the generalized ``inherit={'Parameters': source}`` argument."""
    result = {}
    for key, sources in dict(value or {}).items():
        kind = section_kind(key)
        if kind is None:
            raise DocShareError(
                f'inherit={{{key!r}: ...}} names a section docshare does not '
                f'recognize; inherit an unrecognized section with '
                f'inheritother=[(source, {key!r})] instead'
            )
        result[kind.name] = _as_source_specs(sources)
    return result


def _from_inheritall(value, include_opaque):
    """Expand ``inheritall`` into one operation per section of the sources."""
    specs = _as_source_specs(value)
    if not specs:
        return ({}, ())
    sources = [spec[0] if isinstance(spec, tuple) else spec for spec in specs]
    inherits = {}
    opaque = []
    for source in sources:
        for section in docparse(source).sections:
            if section.kind is not None:
                inherits.setdefault(section.kind, []).append(source)
            elif include_opaque:
                opaque.append((source, section.name))
    return ({k: tuple(v) for (k, v) in inherits.items()}, tuple(opaque))


def _operations(options):
    """Build the ordered operations the decorator's arguments describe."""
    (inherits, drops, maps) = _collect(options)
    general = _from_general_inherit(options.get('inherit'))
    conflicts = sorted(set(general) & set(inherits))
    if conflicts:
        names = ', '.join(f'inherit{_short(kind)}' for kind in conflicts)
        raise DocShareError(
            f'the {conflicts[0]!r} section is named both by inherit= and by '
            f'{names}; give it in one place or the other'
        )
    inherits.update(general)
    other = options.get('inheritother')
    include_opaque = other is True
    (from_all, opaque_from_all) = _from_inheritall(
        options.get('inheritall'), include_opaque
    )
    for kind, sources in from_all.items():
        inherits.setdefault(kind, sources)
    operations = []
    for kind in iter_section_kinds():
        sources = inherits.get(kind.name)
        if not sources:
            continue
        operations.append(
            Operation(
                kind=kind.name,
                sources=sources,
                drop=drops.get(kind.name, frozenset()),
                mapping=maps.get(kind.name, {}),
            )
        )
    opaque = list(opaque_from_all)
    if other is not None and other is not True and other is not False:
        for entry in _as_source_specs(other):
            if not (isinstance(entry, tuple) and len(entry) == 2):
                raise DocShareError(
                    'inheritother expects (source, section name) pairs, '
                    f'but got {entry!r}'
                )
            opaque.append(entry)
    for source, name in opaque:
        operations.append(Operation(kind=None, name=name, sources=(source,)))
    return tuple(operations)


def _assign(obj, text):
    """Assign rendered documentation to an object."""
    try:
        obj.__doc__ = text
    except (AttributeError, TypeError) as error:
        raise DocShareError(
            f'docshare cannot assign documentation to {obj!r}: its __doc__ '
            f'is not writable ({error})'
        ) from error


def _apply(obj, options):
    """Compose and install documentation on a single object."""
    for name in options:
        if name not in GENERAL_ARGUMENTS and name not in SECTION_ARGUMENTS:
            _unknown_argument(name)
    format = options.get('format')
    render = options.get('render', format)
    extraparam = options.get('extraparam')
    doc = docparse(obj, format=format)
    validate_signature(
        obj,
        doc,
        extraparam=extraparam,
        parammap=options.get('parammap'),
    )
    operations = _operations(options)
    if not operations:
        # Nothing was composed, so the docstring is left exactly as written.
        set_docinfo(obj, doc)
        return obj
    composed = compose(obj, doc, operations, extraparam=extraparam)
    _assign(obj, render_document(composed, format=render))
    set_docinfo(obj, composed)
    return obj


def docshare(obj=None, /, **options):
    """Compose an object's documentation from itself and its sources.

    The decorator may be used bare, when it only parses and validates the
    documentation, or called with arguments describing what to inherit.
    Documentation the object provides for itself is always kept; a source
    fills only what the object leaves out.

    Parameters
    ----------
    obj : object, optional
        The object to document. This is supplied by Python when the
        decorator is used bare, and may be given directly to compose an
        object's documentation outside a decorator expression.
    format : str, optional
        The format the object's own docstring is written in. The default
        detects it, which is not possible for an object that has no
        docstring of its own.
    render : str, optional
        The format the composed documentation is written in. The default is
        `format`, or the detected format when `format` was not given, so
        that a docstring is normally written back in the style it was
        written in. Giving `render` on its own says how to write an object
        that has no docstring to detect a format from; giving both converts
        a document from one format into the other.
    inherit : mapping, optional
        The generalized form, mapping a section name to its sources, as in
        ``inherit={'Parameters': other}``.
    inheritall : object or sequence, optional
        Inherit every recognized section the sources document.
    inheritother : sequence or bool, optional
        Inherit unrecognized sections, which are never inherited otherwise.
        Give ``(source, 'Section Name')`` pairs, or ``True`` alongside
        `inheritall` to take every unrecognized section the sources have.
    extraparam : str or sequence of str, optional
        Parameters documented deliberately although the signature does not
        name them, typically because they are taken from ``**kwargs``.
    **options
        Per-section arguments. Every section accepts ``inherit<short>``, and
        every section holding items also accepts ``drop<short>`` and
        ``<singular>map``: `inheritparams`, `dropparams`, and `parammap` for
        Parameters, `inheritreturns`, `dropreturns`, and `returnmap` for
        Returns, and so on.

    Returns
    -------
    object
        The object itself, with its ``__doc__`` replaced when anything was
        composed, or a decorator when `obj` was not given.

    Raises
    ------
    DocShareError
        If an argument is not recognized or is given in two places.
    DocFormatError
        If the format is unsupported, cannot be detected, or is needed for
        rendering and was not given.
    DocSignatureError
        If the documentation describes a parameter the object does not have.
    DocInheritanceError
        If the requested inheritance is incoherent.
    DocMappingError
        If a mapping or a bound source is invalid.
    """
    if obj is not None:
        return _apply(obj, options)

    def decorate(target):
        return _apply(target, options)

    return decorate
