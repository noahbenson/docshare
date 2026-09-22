# -*- coding: utf-8 -*-
################################################################################
# docshare/_decorator.py
#
# The docshare decorator itself.

"""The `docwrap` decorator.

`docwrap` is the whole library seen from the outside: it parses the
decorated object's documentation, performs the inheritance the caller asked
for, renders the result, and assigns it back. Everything it accepts is
shorthand for the generalized inheritance the library performs, and the
shorthand is generated from the section registry rather than written out
section by section, so that the vocabulary is uniform.

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
`docshare`'s control.
"""

from __future__ import annotations

import difflib
import keyword
from collections.abc import Callable, Mapping
from typing import Any, TypeVar, overload

from ._cache import docinfo, docparse, set_docinfo, source_document
from ._exceptions import DocShareError
from ._inherit import DESCRIPTION, SUMMARY, Operation, compose
from ._model import Document, FrozenDict
from ._render import render_document
from ._sections import (
    SUPPORTED_FORMATS,
    iter_section_kinds,
    normalize_custom,
    normalize_title,
    section_kind,
)
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
    'custom',
    'sourcecustom',
    'sourceformat',
    'inheritcustom',
    'ignorecustom',
    'custommap',
)

#: The per-section arguments that name a custom section in a mapping, so
#: that a section whose title is not a Python name can still be addressed.
CUSTOM_ARGUMENTS = {
    'inheritcustom': 'inherit',
    'ignorecustom': 'drop',
    'custommap': 'map',
}


def custom_arguments(declared):
    """Build the per-section arguments a declaration adds to the vocabulary.

    A declared section gets the same three arguments a recognized one has,
    generated from its title the same way, so that ``Inputs`` is addressed
    as `inheritinputs` rather than through a mapping. That is only possible
    when the title is a Python name: a title of several words, or one
    carrying a hyphen, has no such spelling and is addressed by
    `inheritcustom` and its companions instead, which every declared section
    accepts.

    These are conveniences, so a title that cannot have them is not an
    error. A collision is: two names that generate the same argument, or one
    that generates an argument `docshare` already has, would otherwise make
    one of them silently unreachable.

    Parameters
    ----------
    declared : Mapping or None
        A normalized declaration, as `normalize_custom` returns.

    Returns
    -------
    dict
        Each generated argument name, mapped to its role and section kind,
        in the shape `SECTION_ARGUMENTS` uses.

    Raises
    ------
    DocShareError
        If a generated name collides with an existing argument or with one
        generated for another declared section.
    """
    table = {}
    owners = {}
    for key, kind in (declared or {}).items():
        if kind is None or not key.isidentifier() or keyword.iskeyword(key):
            # A section with no semantics has nothing to map or exclude, and
            # a title that is not a name has no short spelling.
            continue
        names = {f'inherit{key}': ('inherit', kind.name)}
        if kind.structured:
            names[f'ignore{key}'] = ('drop', kind.name)
            names[_map_name(key)] = ('map', kind.name)
        for name in names:
            if name in SECTION_ARGUMENTS or name in GENERAL_ARGUMENTS:
                raise DocShareError(
                    f'the custom section {key!r} would be addressed as '
                    f'{name}=, which docwrap already accepts for something '
                    f'else; rename the section, or address it with '
                    f'inheritcustom={{{key!r}: ...}}'
                )
            if name in table:
                raise DocShareError(
                    f'the custom sections {owners[name]!r} and {key!r} would '
                    f'both be addressed as {name}=; rename one, or address '
                    f'them with inheritcustom={{...}}'
                )
            owners[name] = key
        table.update(names)
    return table


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


def _source_of(spec):
    """Return the source object of a normalized source specification."""
    return spec[0] if isinstance(spec, tuple) and len(spec) == 2 else spec


class _Sources:
    """Resolves each inheritance source to a document, once per call.

    Parsing belongs here rather than in the inheritance engine. The engine
    composes documents; deciding how a source is *read* --- which format it
    is written in, and which sections it declares --- is the decorator's
    business, because that is where the caller says so. Resolving every
    source before any operation is built also means each source is parsed
    once, under everything the call said about it, rather than once per
    argument that happens to name it.

    Parameters
    ----------
    plan : Mapping, optional
        How each source is read, keyed by the source's identity, as
        `_source_plan` builds it. A source the plan says nothing about is
        read as it always was: its format detected, and no sections declared
        beyond the recognized ones.
    """

    __slots__ = ('_documents', '_plan')

    def __init__(self, plan=None):
        # Keyed by identity, because a source is an arbitrary object and
        # need not be comparable. The object is kept alongside its document
        # so that it stays alive, and its identity therefore stays unique,
        # for as long as this resolver does.
        self._documents = {}
        self._plan = plan or {}

    def document(self, source):
        """Return the document for one source object."""
        if isinstance(source, Document):
            return source
        found = self._documents.get(id(source))
        if found is None:
            (format, custom) = self._plan.get(id(source), (None, None))
            if format is None and custom is None:
                document = source_document(source)
            else:
                document = docinfo(source, format=format, custom=custom)
            found = (source, document)
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


def _named_sources(options, custom_args):
    """Yield ``(source, title)`` for every source the arguments name.

    `title` is the declared section the argument is about, normalized, when
    the argument is about one; it is ``None`` for an argument that names no
    particular section, such as `inheritall`.
    """
    for name, value in options.items():
        if name == 'inheritcustom':
            for key, entry in dict(value or {}).items():
                title = normalize_title(key)
                for spec in _as_source_specs(entry):
                    yield (_source_of(spec), title)
            continue
        if name == 'inherit':
            for entry in dict(value or {}).values():
                for spec in _as_source_specs(entry):
                    yield (_source_of(spec), None)
            continue
        if name in SECTION_ARGUMENTS:
            if SECTION_ARGUMENTS[name][0] != 'inherit':
                continue
            title = None
        elif name in custom_args:
            (role, kind) = custom_args[name]
            if role != 'inherit':
                continue
            title = kind.replace('_', ' ')
        elif name in ('inheritall', 'inheritsummary', 'inheritdescription'):
            title = None
        elif name == 'inheritother':
            if not isinstance(value, (tuple, list)):
                continue
            title = None
        else:
            continue
        for spec in _as_source_specs(value):
            yield (_source_of(spec), title)


def _as_source_set(value, label):
    """Normalize an argument naming sources into a list of objects."""
    if value is None:
        return []
    entries = list(value) if isinstance(value, (tuple, list)) else [value]
    for entry in entries:
        if isinstance(entry, Document):
            raise DocShareError(
                f'{label} names an already-parsed document, which was read '
                f'when it was parsed and cannot be read again; pass the '
                f'object it came from, or parse it the way you want it'
            )
    return entries


def _source_plan(options, declared, custom_args):
    """Decide how each inheritance source is read.

    Three things say how a source should be read, and they are unioned per
    source rather than applied per argument, so that a source named by two
    arguments is one document rather than two.

    An argument that names a declared section says so by naming it:
    ``inheritinputs=fn`` cannot mean anything unless `fn` is read with
    ``Inputs`` declared. `sourcecustom` says which sources share the whole
    declaration, which is what `inheritall` and the other arguments that
    name no section need. `sourceformat` says which format a source is
    written in, for a docstring whose format cannot be detected.

    Parameters
    ----------
    options : Mapping
        The decorator's arguments.
    declared : Mapping or None
        The normalized declaration, as `normalize_custom` returns.
    custom_args : Mapping
        The generated per-section arguments, as `custom_arguments` returns.

    Returns
    -------
    dict
        ``{id(source): (format, custom)}`` for every source the call says
        something about, where `custom` is the part of the declaration that
        applies to that source. Keying by identity is safe because every
        source is held by the arguments themselves for as long as the plan
        is used.

    Raises
    ------
    DocShareError
        If a source named by `sourcecustom` or `sourceformat` is an
        already-parsed document, or if a format is not one docshare
        supports.
    """
    titles = {}
    formats = {}
    named = list(_named_sources(options, custom_args))
    for source, title in named:
        if title is not None and declared and title in declared:
            titles.setdefault(id(source), set()).add(title)
    shared = options.get('sourcecustom')
    if shared is not None and shared is not False:
        if isinstance(shared, Mapping):
            for key, value in shared.items():
                title = normalize_title(key)
                if not declared or title not in declared:
                    raise DocShareError(
                        f'sourcecustom names the section {key!r}, which '
                        f'custom= does not declare'
                    )
                for source in _as_source_set(value, 'sourcecustom'):
                    titles.setdefault(id(source), set()).add(title)
        else:
            every = set(declared or ())
            if shared is True:
                chosen = [source for (source, _) in named]
            else:
                chosen = _as_source_set(shared, 'sourcecustom')
            for source in chosen:
                titles.setdefault(id(source), set()).update(every)
    source_format = options.get('sourceformat')
    if source_format is not None:
        if isinstance(source_format, Mapping):
            pairs = list(source_format.items())
        else:
            pairs = [(source_format, [s for (s, _) in named])]
        for format, value in pairs:
            if format not in SUPPORTED_FORMATS:
                raise DocShareError(
                    f'sourceformat names {format!r}, which is not a '
                    f'documentation format; expected one of '
                    f'{", ".join(map(repr, SUPPORTED_FORMATS))}'
                )
            for source in _as_source_set(value, 'sourceformat'):
                formats[id(source)] = format
    plan = {}
    for key in set(titles) | set(formats):
        chosen = titles.get(key)
        custom = (
            FrozenDict({t: declared[t] for t in sorted(chosen)})
            if chosen
            else None
        )
        plan[key] = (formats.get(key), custom)
    return plan


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


def _unknown_argument(name, custom_args=None):
    """Raise a helpful error for an argument `docshare` does not accept."""
    custom_args = custom_args or {}
    (intended, prefix) = _wrong_exclude_prefix(name)
    if intended is not None:
        kind = SECTION_ARGUMENTS[intended][1]
        title = kind.replace('_', ' ').title()
        raise DocShareError(
            f'docwrap() got an unexpected argument {name!r}; use '
            f'{intended}= instead. The {title} section '
            f'{_EXCLUDE_REASON[prefix]}'
        )
    known = sorted(
        set(SECTION_ARGUMENTS) | set(GENERAL_ARGUMENTS) | set(custom_args)
    )
    close = difflib.get_close_matches(name, known, n=3, cutoff=0.6)
    hint = f'; did you mean {" or ".join(map(repr, close))}?' if close else ''
    raise DocShareError(f'docwrap() got an unexpected argument {name!r}{hint}')


def _collect(options, sources, custom_args):
    """Sort the decorator's per-section arguments by role and kind.

    Every name is known to be valid: `_apply` rejects unrecognized arguments
    before any work is done. A generated argument is indistinguishable from
    a built-in one here, which is the point of generating it.
    """
    inherits = {}
    drops = {}
    maps = {}
    for name, value in options.items():
        entry = SECTION_ARGUMENTS.get(name) or custom_args.get(name)
        if entry is None:
            continue
        (role, kind) = entry
        if role == 'inherit':
            inherits[kind] = sources.resolve_all(value)
        elif role == 'drop':
            drops[kind] = _as_identities(value)
        else:
            maps[kind] = dict(value or {})
    return (inherits, drops, maps)


def _from_custom_mappings(options, declared, sources):
    """Expand ``inheritcustom`` and its companions, which are keyed by title.

    Every declared section is addressable this way, including one whose
    title has no spelling as an argument name and one declared without a
    kind, which has no semantics and is inherited whole.
    """
    inherits = {}
    drops = {}
    maps = {}
    opaque = []
    for argument, role in CUSTOM_ARGUMENTS.items():
        for key, value in dict(options.get(argument) or {}).items():
            title = normalize_title(key)
            if not declared or title not in declared:
                raise DocShareError(
                    f'{argument} names the section {key!r}, which custom= '
                    f'does not declare'
                )
            kind = declared[title]
            if kind is None:
                if role != 'inherit':
                    raise DocShareError(
                        f'{argument} names the section {key!r}, which is '
                        f'declared without a kind and so has no items to '
                        f'exclude or rename; it is inherited whole'
                    )
                for spec in _as_source_specs(value):
                    opaque.append(
                        (sources.document(_source_of(spec)), str(key).strip())
                    )
                continue
            if role == 'inherit':
                inherits[kind.name] = sources.resolve_all(value)
            elif role == 'drop':
                drops[kind.name] = _as_identities(value)
            else:
                maps[kind.name] = dict(value or {})
    return (inherits, drops, maps, opaque)


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


def _operations(options, sources, declared=None, custom_args=None):
    """Build the ordered operations the decorator's arguments describe."""
    custom_args = custom_args or {}
    (inherits, drops, maps) = _collect(options, sources, custom_args)
    (from_custom, custom_drops, custom_maps, custom_opaque) = (
        _from_custom_mappings(options, declared, sources)
    )
    conflicts = sorted(set(from_custom) & set(inherits))
    if conflicts:
        raise DocShareError(
            f'the {conflicts[0]!r} section is named both by inheritcustom= '
            f'and by an argument of its own; give it in one place or the '
            f'other'
        )
    inherits.update(from_custom)
    drops.update(custom_drops)
    maps.update(custom_maps)
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
    # A declared section is composed after the recognized ones, in the order
    # it was declared, so that the order is the caller's rather than an
    # accident of how the operations were built.
    for kind in (declared or {}).values():
        if kind is None:
            continue
        documents = inherits.get(kind.name)
        if not documents:
            continue
        operations.append(
            Operation(
                kind=kind.name,
                sources=documents,
                drop=drops.get(kind.name, frozenset()),
                mapping=maps.get(kind.name, {}),
                custom=kind,
            )
        )
    opaque = list(opaque_from_all) + list(custom_opaque)
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
    """Compose and install documentation on a single object.

    The order matters. What the call declares decides which arguments it may
    use, so the declaration is read first; the arguments are then checked
    against a vocabulary that includes the generated ones; how each source
    is read is settled before any source is read; and only then is anything
    composed.
    """
    declared = normalize_custom(options.get('custom'))
    custom_args = custom_arguments(declared)
    for name in options:
        if (
            name not in GENERAL_ARGUMENTS
            and name not in SECTION_ARGUMENTS
            and name not in custom_args
        ):
            _unknown_argument(name, custom_args)
    format = options.get('format')
    render = options.get('render', format)
    extraparam = options.get('extraparam')
    doc = docparse(obj, format=format, custom=options.get('custom'))
    validate_signature(
        obj,
        doc,
        extraparam=extraparam,
        parammap=options.get('parammap'),
    )
    sources = _Sources(_source_plan(options, declared, custom_args))
    operations = _operations(options, sources, declared, custom_args)
    if not operations:
        # Nothing was composed, so the docstring is left exactly as written.
        set_docinfo(obj, doc, format=format, custom=declared)
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
        obj,
        composed.evolve(format=written),
        text=text,
        format=written,
        custom=declared,
    )
    return obj


_T = TypeVar('_T')


@overload
def docwrap(obj: _T, /, **options: Any) -> _T: ...
@overload
def docwrap(obj: None = ..., /, **options: Any) -> Callable[[_T], _T]: ...
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
    custom : mapping, iterable of str, or str, optional
        Sections this object's documentation has beyond the ones `docshare`
        recognizes. Each title either names the recognized section it
        resembles, borrowing how its body is read, or is given alone, which
        recognizes the title as a section and leaves its body
        uninterpreted. Nothing is registered: what one call declares cannot
        change how anything else is read.

        A declared section is addressed as `inheritcustom` and its
        companions, and, when its title is a Python name, by arguments
        generated from it exactly as for a recognized section:
        ``Inputs`` offers `inheritinputs`, `ignoreinputs`, and `inputmap`.
    sourcecustom : bool, object, sequence, or mapping, optional
        Which sources share the declaration. A source named by an argument
        that names a declared section is read with that section already,
        since the argument means nothing otherwise; this is for the
        arguments that name no section, above all `inheritall`. Give
        ``True`` for every source, one or more sources for all of the
        declaration, or a mapping from a declared title to the sources it
        applies to.
    sourceformat : str or mapping, optional
        The format a source is written in, for a docstring whose format
        cannot be detected. Give one format for every source, or a mapping
        from a format to the sources written in it. There is no default:
        a source's format is detected, so that inheriting across the two
        formats keeps working.
    inheritcustom : mapping, optional
        Inherit declared sections, as ``{'Inputs': source}``. Every
        declared section can be addressed this way, including one whose
        title is not a Python name and one declared without a kind.
    ignorecustom : mapping, optional
        Exclude items of a declared section from inheritance, as
        ``{'Inputs': 'x'}``. A declared section is driven by its sources,
        so this names one of *theirs*.
    custommap : mapping, optional
        Rename items of a declared section, as
        ``{'Inputs': {'data': 'x'}}``.
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
