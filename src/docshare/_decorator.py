# -*- coding: utf-8 -*-
################################################################################
# docshare/_decorator.py
#
# The docshare decorator itself.

"""The `docwrap` decorator.

`docwrap` is the whole library seen from the outside: it parses the
decorated object's documentation, performs the inheritance the caller asked
for, renders the result, and assigns it back. Everything it accepts is
shorthand for the generalized inheritance described in specification section
43, and the shorthand is generated from the section registry rather than
written out section by section, so that the vocabulary is uniform.

For a section named by its short form --- ``params`` for Parameters,
``seealso`` for See Also, and so on --- the decorator accepts
``inherit<short>`` for every section, and for a section that holds items also
``<singular>map`` and an argument that excludes an item from inheritance.

That last one is named for the side it acts on. A section documenting the
callable's parameters is driven by the signature, so ``drop<short>`` names
one of the target's own parameters: Parameters offers `inheritparams`,
`dropparams`, and `parammap`. Every other section is driven by its sources,
so ``ignore<short>`` names one of the source's items: Raises offers
`inheritraises`, `ignoreraises`, and `raisemap`.

Composition happens once, when the decorator runs. Nothing is recomputed
afterwards, and a docstring assigned later by another decorator is outside
`docshare`'s control, as specification sections 34 and 35 describe.
"""

from __future__ import annotations

import difflib

from ._cache import docparse, set_docinfo, source_document
from ._exceptions import DocShareError
from ._inherit import DESCRIPTION, SUMMARY, Operation, compose
from ._model import Document
from ._render import render_document
from ._sections import iter_section_kinds, section_kind
from ._signature import PARAMETER_KINDS, validate_signature

__all__ = ('docwrap',)


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


def _exclude_prefix(kind_name):
    """Return the prefix a section's exclusion argument is named with.

    A section that documents a callable's parameters is driven by the
    signature: the target says what exists and a source only fills it in, so
    the useful exclusion names one of the target's own parameters and is
    called ``drop``. Every other section is driven by its sources, which
    decide what exists, so the useful exclusion names one of the source's
    items and is called ``ignore``.

    The two are never interchangeable. Excluding a source parameter would do
    nothing, because a parameter the target does not have is never inherited
    to begin with; and excluding a target item in a source-driven section
    would do nothing either, because the target's own documentation is kept
    regardless. Naming them differently keeps that from being something a
    caller has to remember.
    """
    return 'drop' if kind_name in PARAMETER_KINDS else 'ignore'


def _build_arguments():
    """Build the table of per-section arguments the decorator accepts."""
    table = {}
    for kind in iter_section_kinds():
        short = _short(kind.name)
        table[f'inherit{short}'] = ('inherit', kind.name)
        if kind.structured:
            prefix = _exclude_prefix(kind.name)
            table[f'{prefix}{short}'] = ('drop', kind.name)
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
    'inheritsummary',
    'inheritdescription',
    'extraparam',
)

#: Maps the arguments naming a document component to that component.
COMPONENT_ARGUMENTS = {
    'inheritsummary': SUMMARY,
    'inheritdescription': DESCRIPTION,
}


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


class _Sources:
    """Resolves each inheritance source to a document, once per call.

    Parsing belongs here rather than in the inheritance engine. The engine
    composes documents; deciding how a source is *read* --- which format it
    is written in, and which sections it declares --- is the decorator's
    business, because that is where the caller says so. Resolving every
    source before any operation is built also means each source is parsed
    once, whatever number of arguments name it.
    """

    __slots__ = ('_documents',)

    def __init__(self):
        # Keyed by identity, because a source is an arbitrary object and
        # need not be comparable. The object is kept alongside its document
        # so that it stays alive, and its identity therefore stays unique,
        # for as long as this resolver does.
        self._documents = {}

    def document(self, source):
        """Return the document for one source object."""
        if isinstance(source, Document):
            return source
        found = self._documents.get(id(source))
        if found is None:
            found = (source, source_document(source))
            self._documents[id(source)] = found
        return found[1]

    def resolve(self, entry):
        """Resolve one source specification, keeping any item binding."""
        if isinstance(entry, tuple) and len(entry) == 2:
            (obj, key) = entry
            return (self.document(obj), key)
        return self.document(entry)

    def resolve_all(self, value):
        """Normalize and resolve an inheritance-source argument."""
        return tuple(self.resolve(e) for e in _as_source_specs(value))


def _as_identities(value):
    """Normalize a drop argument into a frozenset of identities."""
    if value is None:
        return frozenset()
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        return frozenset({value})
    return frozenset(value)


#: Why each exclusion prefix belongs to the sections it belongs to.
_EXCLUDE_REASON = {
    'drop': (
        'is ordered by the signature, so an exclusion names one of the '
        "target's own parameters. Excluding one of the source's would do "
        'nothing, since a parameter the target does not have is never '
        'inherited anyway'
    ),
    'ignore': (
        'is driven by its sources, which decide what items exist, so an '
        "exclusion names one of the source's items. Excluding one of the "
        "target's would do nothing, since the target's own documentation is "
        'kept regardless'
    ),
}


def _wrong_exclude_prefix(name):
    """Return the argument `name` was meant to be, if it has the other prefix.

    `dropreturns` and `ignoreparams` are the two mistakes this vocabulary
    invites, and each has exactly one right answer, so they are worth
    answering specifically rather than by resemblance.
    """
    for wrong, right in (('ignore', 'drop'), ('drop', 'ignore')):
        if not name.startswith(wrong):
            continue
        intended = right + name[len(wrong) :]
        if intended in SECTION_ARGUMENTS:
            return (intended, right)
    return (None, None)


def _unknown_argument(name):
    """Raise a helpful error for an argument `docshare` does not accept."""
    (intended, prefix) = _wrong_exclude_prefix(name)
    if intended is not None:
        kind = SECTION_ARGUMENTS[intended][1]
        title = kind.replace('_', ' ').title()
        raise DocShareError(
            f'docwrap() got an unexpected argument {name!r}; use '
            f'{intended}= instead. The {title} section '
            f'{_EXCLUDE_REASON[prefix]}'
        )
    known = sorted(set(SECTION_ARGUMENTS) | set(GENERAL_ARGUMENTS))
    close = difflib.get_close_matches(name, known, n=3, cutoff=0.6)
    hint = f'; did you mean {" or ".join(map(repr, close))}?' if close else ''
    raise DocShareError(f'docwrap() got an unexpected argument {name!r}{hint}')


def _collect(options, sources):
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
            inherits[kind] = sources.resolve_all(value)
        elif role == 'drop':
            drops[kind] = _as_identities(value)
        else:
            maps[kind] = dict(value or {})
    return (inherits, drops, maps)


def _from_general_inherit(value, sources):
    """Expand the generalized ``inherit={'Parameters': source}`` argument."""
    result = {}
    for key, entry in dict(value or {}).items():
        kind = section_kind(key)
        if kind is None:
            raise DocShareError(
                f'inherit={{{key!r}: ...}} names a section docshare does not '
                f'recognize; inherit an unrecognized section with '
                f'inheritother=[(source, {key!r})] instead'
            )
        result[kind.name] = sources.resolve_all(entry)
    return result


def _from_inheritall(value, include_opaque, sources):
    """Expand ``inheritall`` into one operation per section of the sources."""
    specs = _as_source_specs(value)
    if not specs:
        return ({}, ())
    inherits = {}
    opaque = []
    for spec in specs:
        # An item binding says nothing about which sections a source has.
        entry = spec[0] if isinstance(spec, tuple) else spec
        doc = sources.document(entry)
        for section in doc.sections:
            if section.kind is not None:
                inherits.setdefault(section.kind, []).append(doc)
            elif include_opaque and section.name:
                # A prose block between sections has no name to ask for.
                opaque.append((doc, section.name))
    return ({k: tuple(v) for (k, v) in inherits.items()}, tuple(opaque))


def _component_operations(options, sources):
    """Build the operations inheriting the summary and the description.

    These are not sections, so they are never implied by inheriting one.
    They are asked for by name, or by `inheritall`, which means all of a
    source's documentation and would be a strange way to spell all of it but
    the first line.
    """
    components = {}
    for name, component in COMPONENT_ARGUMENTS.items():
        specs = sources.resolve_all(options.get(name))
        if specs:
            components[component] = specs
    from_all = sources.resolve_all(options.get('inheritall'))
    if from_all:
        for component in COMPONENT_ARGUMENTS.values():
            components.setdefault(component, from_all)
    return tuple(
        Operation(kind=component, sources=components[component])
        for component in COMPONENT_ARGUMENTS.values()
        if component in components
    )


def _operations(options, sources):
    """Build the ordered operations the decorator's arguments describe."""
    (inherits, drops, maps) = _collect(options, sources)
    general = _from_general_inherit(options.get('inherit'), sources)
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
        options.get('inheritall'), include_opaque, sources
    )
    for kind, documents in from_all.items():
        inherits.setdefault(kind, documents)
    # The summary and the description open the document, so they are
    # composed before the sections that follow them.
    operations = list(_component_operations(options, sources))
    for kind in iter_section_kinds():
        documents = inherits.get(kind.name)
        if not documents:
            continue
        operations.append(
            Operation(
                kind=kind.name,
                sources=documents,
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
            opaque.append((sources.document(entry[0]), entry[1]))
    for doc, name in opaque:
        operations.append(Operation(kind=None, name=name, sources=(doc,)))
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
    operations = _operations(options, _Sources())
    if not operations:
        # Nothing was composed, so the docstring is left exactly as written.
        set_docinfo(obj, doc, format=format)
        return obj
    composed = compose(obj, doc, operations, extraparam=extraparam)
    # Inheritance into a signature-ordered section cannot invent a parameter,
    # but a section that is driven by its sources could, so the composed
    # document is checked before it is installed.
    validate_signature(
        obj,
        composed,
        extraparam=extraparam,
        parammap=options.get('parammap'),
    )
    text = render_document(composed, format=render)
    _assign(obj, text)
    # The record describes the documentation that was just written, so it
    # carries the format that was written rather than the one that was read.
    written = render if render is not None else composed.format
    set_docinfo(
        obj, composed.evolve(format=written), text=text, format=written
    )
    return obj


def docwrap(obj=None, /, **options):
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
        Inherit every recognized section the sources document, along with
        their summary and description.
    inheritsummary : object or sequence, optional
        Inherit the sources' summary, which is otherwise never inherited.
        This is implied by `inheritall`.
    inheritdescription : object or sequence, optional
        Inherit the sources' description --- the prose between the summary
        and the first section --- which is otherwise never inherited. This
        is implied by `inheritall`.
    inheritother : sequence or bool, optional
        Inherit unrecognized sections, which are never inherited otherwise.
        Give ``(source, 'Section Name')`` pairs, or ``True`` alongside
        `inheritall` to take every unrecognized section the sources have.
    extraparam : str or sequence of str, optional
        Parameters documented deliberately although the signature does not
        name them, typically because they are taken from ``**kwargs``.
    **options
        Per-section arguments. Every section accepts ``inherit<short>``, and
        every section holding items also accepts ``<singular>map`` and an
        exclusion. A section documenting the callable's parameters is driven
        by the signature, so its exclusion names one of the target's own
        parameters and is called ``drop<short>``: `inheritparams`,
        `dropparams`, and `parammap`. Every other section is driven by its
        sources, so its exclusion names one of the source's items and is
        called ``ignore<short>``: `inheritreturns`, `ignorereturns`, and
        `returnmap`.

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
