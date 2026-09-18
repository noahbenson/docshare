# -*- coding: utf-8 -*-
################################################################################
# docshare/_cache.py
#
# docparse, docinfo, and the package-level documentation cache.

"""Parsed documentation, and the cache that remembers it.

`docparse` reads an object's documentation and parses it from scratch every
time. `docinfo` answers the same question from a package-level cache,
parsing only when it has nothing recorded. The two are separate because
composition records its *result*: after a document has been assembled from
inherited sections, `docinfo` reports the assembled document, which is what a
later object inheriting from it needs.

The cache is keyed by the documentation text itself rather than by the object
that carries it. That follows from what a parsed document depends on: nothing
but the text it was parsed from. Two objects documented identically therefore
share one entry, correctly, and an object whose docstring is reassigned
simply misses and is parsed again --- which it would have to be in any case.

Keying this way also means the cache never refers to the objects it
describes, so it cannot keep one alive and there is no object it cannot
handle. It does hold the documentation strings, which cannot be weakly
referenced, so it is bounded: the least recently used entry is discarded when
it is full. The bound is generous, and losing an entry costs only a reparse.

The cache is the library's only shared mutable state, and it is synchronized.
Everything else `docshare` touches is either built once at import and read
thereafter, such as the section registry, or belongs to the caller. Two
threads importing two modules that each use `docshare` therefore contend only
here.

Parsing itself happens outside the lock. Two threads that ask for the same
unrecorded documentation at the same time will both parse it, and one will
replace the other's entry; since a document depends only on the text it came
from, the two are equivalent and either will do. Holding the lock across
parsing would serialize the work this cache exists to avoid.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import MutableMapping

from ._parser import parse_document

__all__ = ('DocCache', 'clear_docinfo', 'doccache', 'docinfo', 'docparse')


#: The number of documents remembered before the oldest is discarded.
DEFAULT_MAXSIZE = 2048


class DocCache(MutableMapping):
    """A bounded cache of parsed documentation, keyed by documentation text.

    The cache behaves as an ordinary mutable mapping from a docstring to the
    `Document` it parses to, discarding the least recently used entry when it
    grows past `DocCache.maxsize`.

    An instance of this class is exposed as `docshare.doccache`. It is public
    so that it can be inspected, cleared, resized, or pre-loaded, all of which
    have legitimate uses; it is nonetheless the library's own working state,
    and putting a document into it that does not correspond to its key will
    produce documentation that does not correspond to anything.

    Every operation is atomic with respect to other threads. Looking an entry
    up also marks it as recently used, and discarding entries walks the whole
    cache, so neither is a single dictionary operation and neither would be
    safe unsynchronized. Iteration, and the views built on it, work from a
    snapshot, so another thread may add or discard entries while one is being
    walked without either interfering with the other.

    Parameters
    ----------
    maxsize : int, optional
        The number of entries to keep; the default is `DEFAULT_MAXSIZE`. A
        value of zero disables caching.
    """

    __slots__ = ('_entries', '_lock', '_maxsize')

    def __init__(self, maxsize=DEFAULT_MAXSIZE):
        self._entries = OrderedDict()
        self._maxsize = max(0, int(maxsize))
        self._lock = threading.Lock()

    @property
    def maxsize(self):
        """The number of entries kept before the oldest is discarded (`int`).

        Lowering this discards the least recently used entries at once.
        """
        return self._maxsize

    @maxsize.setter
    def maxsize(self, value):
        with self._lock:
            self._maxsize = max(0, int(value))
            self._evict()

    def _evict(self):
        """Discard the least recently used entries down to the bound.

        The caller must hold the lock.
        """
        while len(self._entries) > self._maxsize:
            self._entries.popitem(last=False)

    def __getitem__(self, key):
        with self._lock:
            document = self._entries[key]
            self._entries.move_to_end(key)
            return document

    def __setitem__(self, key, value):
        with self._lock:
            if self._maxsize == 0:
                return
            self._entries[key] = value
            self._entries.move_to_end(key)
            self._evict()

    def __delitem__(self, key):
        with self._lock:
            del self._entries[key]

    def __iter__(self):
        with self._lock:
            keys = tuple(self._entries)
        return iter(keys)

    def __len__(self):
        with self._lock:
            return len(self._entries)

    def __contains__(self, key):
        with self._lock:
            return key in self._entries

    def clear(self):
        """Discard every entry.

        Returns
        -------
        None
        """
        with self._lock:
            self._entries.clear()

    def items(self):
        """Return the cache's entries as a snapshot.

        Returns
        -------
        tuple of (str, Document)
            The entries at the moment of the call, oldest first.
        """
        with self._lock:
            return tuple(self._entries.items())

    def values(self):
        """Return the cached documents as a snapshot.

        Returns
        -------
        tuple of Document
            The documents at the moment of the call, oldest first.
        """
        with self._lock:
            return tuple(self._entries.values())

    def keys(self):
        """Return the cached documentation as a snapshot.

        Returns
        -------
        tuple of str
            The keys at the moment of the call, oldest first.
        """
        with self._lock:
            return tuple(self._entries)

    def __repr__(self):
        with self._lock:
            count = len(self._entries)
        return (
            f'{type(self).__name__}(maxsize={self._maxsize}) with '
            f'{count} entries'
        )


#: The documentation `docshare` has parsed, keyed by documentation text.
doccache = DocCache()


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

    When nothing is recorded for the object's documentation, it is parsed
    with `docparse` and the result is recorded before being returned. When
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
    text = documentation(obj)
    try:
        return doccache[text]
    except KeyError:
        pass
    info = parse_document(text, format=format)
    doccache[text] = info
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
    None
    """
    doccache[documentation(obj) if text is None else text] = info


def clear_docinfo(obj=None):
    """Forget recorded documentation.

    Parameters
    ----------
    obj : object, optional
        The object whose documentation should be forgotten. The default
        forgets everything, which is chiefly useful in tests.

    Returns
    -------
    None
    """
    if obj is None:
        doccache.clear()
        return
    doccache.pop(documentation(obj), None)
