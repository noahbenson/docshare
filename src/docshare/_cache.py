# -*- coding: utf-8 -*-
################################################################################
# docshare/_cache.py
#
# docparse, docinfo, and the package-level documentation cache.

"""Parsed documentation, and the cache that remembers it.

`docparse` reads an object's documentation and parses it from scratch every
time. `docinfo` answers the same question from a package-level cache,
parsing only when it has nothing recorded. The two are separate because
composition records its *result* against the composed object: after a
document has been assembled from inherited sections, `docinfo` reports the
assembled document, which is what a later object inheriting from it needs.

The cache never modifies the objects it describes, as required by
specification section 9. It holds its keys weakly, so caching documentation
does not keep an object alive.

Three of the object types the specification requires support for --- the
objects produced by `staticmethod`, `classmethod`, and `property` --- cannot
themselves be weakly referenced. Each of them wraps a function that can be,
so the cache keys on that underlying function. Bound methods need the same
treatment for the opposite reason: they can be weakly referenced, but a new
one is created on every attribute access, so a reference to one would die
immediately.

Every cached entry records the documentation text it was derived from. An
entry is used only while that text still matches the object's current
``__doc__``, so a docstring reassigned after the fact is noticed rather than
silently reported stale.
"""

from __future__ import annotations

import inspect
import weakref

from ._parser import parse_document

__all__ = ('clear_docinfo', 'docinfo', 'docparse')


#: Parsed documentation, keyed weakly by the object it describes. Each value
#: is a ``(documentation text, Document)`` pair.
_CACHE = weakref.WeakKeyDictionary()


def _is_weakrefable(obj):
    """Return whether `obj` can be the target of a weak reference."""
    try:
        weakref.ref(obj)
    except TypeError:
        return False
    return True


def cache_key(obj):
    """Return the object the cache should key `obj` under.

    A descriptor such as a `property` or the object produced by
    `staticmethod` cannot be weakly referenced, and a bound method is
    recreated on every attribute access. Each of them wraps a function that
    is both stable and weakly referenceable, and that function is used as
    the key.

    Parameters
    ----------
    obj : object
        The documented object.

    Returns
    -------
    object or None
        The key to cache under, or ``None`` if `obj` can neither be weakly
        referenced nor resolved to something that can, in which case its
        documentation is simply parsed afresh each time.
    """
    if isinstance(obj, str):
        return None
    if inspect.ismethod(obj):
        return obj.__func__
    for attribute in ('__func__', 'fget'):
        underlying = getattr(obj, attribute, None)
        if underlying is not None and _is_weakrefable(underlying):
            return underlying
    return obj if _is_weakrefable(obj) else None


def documentation(obj):
    """Return the documentation text of `obj`.

    Parameters
    ----------
    obj : object
        The documented object. A string is taken to *be* documentation
        rather than to have any, so that a docstring can be parsed directly
        without first attaching it to something.

    Returns
    -------
    str or None
        The documentation, or ``None`` if the object has none.
    """
    if isinstance(obj, str):
        return obj
    return getattr(obj, '__doc__', None)


def docparse(obj, *, format=None):
    """Parse an object's current documentation from scratch.

    This never consults the cache and never populates it. Use `docinfo` for
    the cached form.

    Parameters
    ----------
    obj : object
        The documented object, or a docstring to parse directly.
    format : str, optional
        The format the documentation must be written in. When this is
        ``None``, the default, the format is detected from the document.

    Returns
    -------
    Document
        The parsed document. An object whose documentation is ``None`` or
        empty yields an empty document rather than an error.

    Raises
    ------
    DocFormatError
        If `format` is unsupported, if the documentation does not conform to
        an explicitly requested format, or if the format cannot be detected.
    DocParseError
        If the documentation cannot be read as the format requires.
    """
    return parse_document(documentation(obj), format=format)


def docinfo(obj, *, format=None):
    """Return the documentation information associated with an object.

    When nothing is recorded for `obj`, its documentation is parsed with
    `docparse` and the result is recorded before being returned. When
    something *is* recorded, it is returned as it stands.

    Parameters
    ----------
    obj : object
        The documented object, or a docstring to parse directly.
    format : str, optional
        The format to parse with, used only if parsing actually has to
        happen. It is not a request to convert anything: the document
        representation does not depend on the format it was written in, and
        a recorded document is returned whatever this says.

    Returns
    -------
    Document
        The document associated with `obj`.

    Raises
    ------
    DocFormatError
        As `docparse`, when parsing is necessary.
    DocParseError
        As `docparse`, when parsing is necessary.
    """
    key = cache_key(obj)
    text = documentation(obj)
    if key is not None:
        entry = _CACHE.get(key)
        if entry is not None and entry[0] == text:
            return entry[1]
    info = parse_document(text, format=format)
    if key is not None:
        _CACHE[key] = (text, info)
    return info


def set_docinfo(obj, info, text=None):
    """Record documentation information for an object.

    Composition uses this to record the document it assembled, so that
    `docinfo` reports the composed document rather than reparsing the
    rendered docstring.

    Parameters
    ----------
    obj : object
        The documented object.
    info : Document
        The document to record.
    text : str, optional
        The documentation text the record corresponds to. The default reads
        the object's current ``__doc__``, which is correct when the caller
        has already assigned the rendered documentation.

    Returns
    -------
    bool
        Whether the information could be recorded. This is ``False`` for an
        object that cannot be weakly referenced and wraps nothing that can.
    """
    key = cache_key(obj)
    if key is None:
        return False
    _CACHE[key] = (documentation(obj) if text is None else text, info)
    return True


def clear_docinfo(obj=None):
    """Forget recorded documentation.

    Parameters
    ----------
    obj : object, optional
        The object to forget. The default forgets everything, which is
        chiefly useful in tests.

    Returns
    -------
    None
    """
    if obj is None:
        _CACHE.clear()
        return
    key = cache_key(obj)
    if key is not None:
        _CACHE.pop(key, None)
