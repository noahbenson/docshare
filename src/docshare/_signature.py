# -*- coding: utf-8 -*-
################################################################################
# docshare/_signature.py
#
# Checking documented parameters against a callable's signature.

"""Validation of documented parameters against a callable's signature.

The purpose of this check is to catch documentation that has drifted from the
code it describes --- a renamed parameter, a typo, a parameter that was
removed --- not to demand that every parameter be documented. Partial
documentation is legitimate and common, so a parameter the signature has and
the documentation omits is never an error. The reverse is: documentation that
describes a parameter the callable does not accept is either a mistake or
something the author must declare deliberately, which is what `extraparam` is
for.

Some documented parameters are genuinely invisible in a signature, because
they are consumed from ``**kwargs``. Those must be declared rather than
inferred, since the presence of ``**kwargs`` would otherwise excuse every
possible typo.
"""

from __future__ import annotations

import inspect

from ._exceptions import DocMappingError, DocSignatureError

__all__ = (
    'documented_parameters',
    'parameter_names',
    'validate_signature',
)


#: The section kinds whose items document parameters of a callable.
PARAMETER_KINDS = ('parameters', 'other_parameters', 'keyword_arguments')


def as_names(value):
    """Normalize a name or collection of names into a tuple of names.

    Parameters
    ----------
    value : str or iterable of str or None
        A single name, a collection of names, or ``None``.

    Returns
    -------
    tuple of str
        The names, in order.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(name) for name in value)


def strip_stars(name):
    """Return a documented parameter name without its leading stars.

    NumPy and Google documentation conventionally write variadic parameters
    as ``*args`` and ``**kwargs``, while a signature names them ``args`` and
    ``kwargs``.

    Parameters
    ----------
    name : str
        The documented name.

    Returns
    -------
    str
        The name as the signature spells it.
    """
    return name.lstrip('*')


def _signature_target(obj):
    """Return the object whose signature describes `obj`.

    A `classmethod` object is not callable and has no signature of its own,
    and neither has a `property`; each wraps a function that does.
    """
    if isinstance(obj, (classmethod, staticmethod)):
        return obj.__func__
    if isinstance(obj, property):
        return obj.fget
    return obj


def signature_of(obj):
    """Return the signature of `obj`, or ``None`` if it has none.

    Parameters
    ----------
    obj : object
        The documented object.

    Returns
    -------
    inspect.Signature or None
        The signature, or ``None`` when one cannot be determined, in which
        case no validation is possible and none is attempted.
    """
    target = _signature_target(obj)
    if target is None:
        return None
    try:
        return inspect.signature(target)
    except (TypeError, ValueError):
        return None


def parameter_names(obj):
    """Return the parameter names of an object's signature.

    Parameters
    ----------
    obj : object
        The documented object.

    Returns
    -------
    frozenset of str or None
        The names the signature accepts, with variadic parameters named as
        the signature names them, or ``None`` if there is no signature.
    """
    signature = signature_of(obj)
    if signature is None:
        return None
    return frozenset(signature.parameters)


def documented_parameters(doc):
    """Yield every parameter name the document declares.

    Parameters
    ----------
    doc : Document
        The document to inspect.

    Yields
    ------
    tuple of (Section, Item, str)
        The section and item that declared the name, and the name itself as
        written, including any leading stars.
    """
    for section in doc.sections:
        if section.kind not in PARAMETER_KINDS:
            continue
        for item in section.items:
            for name in item.names:
                yield (section, item, name)


def _display(obj):
    """Return a readable name for an object, for use in error messages."""
    target = _signature_target(obj)
    name = getattr(target, '__qualname__', None)
    if name is None:
        name = getattr(target, '__name__', None)
    return name if name is not None else repr(obj)


def _locate(section, item):
    """Describe where in a document an item was declared."""
    if item.grouped:
        declaration = ', '.join(item.names)
        return (
            f'its {section.name!r} section, in the grouped declaration '
            f'{declaration!r}'
        )
    return f'its {section.name!r} section'


def _describe(obj):
    """Return ``name(signature)`` for an object, for use in messages."""
    signature = signature_of(obj)
    if signature is None:
        return _display(obj)
    return f'{_display(obj)}{signature}'


def validate_signature(obj, doc, *, extraparam=None, parammap=None):
    """Check a document's parameters against a callable's signature.

    A parameter the signature accepts but the document does not describe is
    not an error: documenting only some parameters is legitimate. A parameter
    the document describes but the signature does not accept is an error
    unless it is declared through `extraparam`.

    Parameters
    ----------
    obj : object
        The documented object. Validation is skipped when it has no
        determinable signature.
    doc : Document
        The document describing `obj`.
    extraparam : str or iterable of str, optional
        Parameters that are documented deliberately even though the
        signature does not name them, typically because they are consumed
        from ``**kwargs``.
    parammap : mapping, optional
        A target-name to source-name mapping, whose keys name parameters of
        `obj` and are therefore validated alongside the documented ones.

    Returns
    -------
    None

    Raises
    ------
    DocSignatureError
        If the document describes a parameter that the callable does not
        accept and that was not declared through `extraparam`, or if it
        describes the same parameter twice.
    DocMappingError
        If `parammap` names a target parameter that the callable does not
        accept and that was not declared through `extraparam`.
    """
    names = parameter_names(obj)
    if names is None:
        return
    declared = frozenset(strip_stars(n) for n in as_names(extraparam))
    allowed = names | declared
    seen = {}
    for section, item, written in documented_parameters(doc):
        name = strip_stars(written)
        where = _locate(section, item)
        if name in seen:
            raise DocSignatureError(
                f'the documentation of {_display(obj)} describes the '
                f'parameter {written!r} more than once, in the '
                f'{seen[name]!r} section and again in {section.name!r}; '
                f'remove one of them'
            )
        seen[name] = section.name
        if name not in allowed:
            raise DocSignatureError(
                f'the documentation of {_describe(obj)} describes a '
                f'parameter {written!r} in {where}, '
                f'but {_display(obj)} has no such parameter. Correct the '
                f'name, or, if it is documented deliberately because it is '
                f'taken from **kwargs, declare it with '
                f'extraparam={written!r}'
            )
    for target in parammap or {}:
        if strip_stars(str(target)) not in allowed:
            raise DocMappingError(
                f'parammap maps {target!r} to '
                f'{parammap[target]!r}, but {_describe(obj)} has no '
                f'parameter {target!r}. The keys of parammap name '
                f'parameters of the object being documented and its values '
                f'name parameters of the source'
            )
