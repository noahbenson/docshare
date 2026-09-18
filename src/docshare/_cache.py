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
that carries it, together with the format it was asked for. That follows from
what a parsed document depends on: the text, and how that text was read. Two
objects documented identically therefore share one entry, correctly, and an
object whose docstring is reassigned simply misses and is parsed again ---
which it would have to be in any case.

The format belongs in the key because one text can be read two ways. A NumPy
declaration with an empty type has the shape of a Google section header, so a
Parameters section whose last entry is ``notes :`` is a parameter called
`notes` when read as NumPy and the start of a Notes section when read as
Google. Keyed by text alone, whichever format was asked for first would
answer every later request as well, including the correct one.

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

from ._model import Document
from ._parser import parse_document
from ._sections import SUPPORTED_FORMATS

__all__ = ('DocCache', 'clear_docinfo', 'doccache', 'docinfo', 'docparse')


#: The number of documents remembered before the oldest is discarded.
DEFAULT_MAXSIZE = 2048


def _check_key(key):
    """Verify that a cache key is a ``(format, documentation)`` pair.

    A dictionary accepts any hashable key, so a bare docstring used as one
    would be stored without complaint and never read again, leaving the cache
    quietly wrong rather than obviously broken. The shape is therefore
    checked on every access.

    Parameters
    ----------
    key : object
        The key to check.

    Returns
    -------
    None

    Raises
    ------
    TypeError
        If the key is not a ``(format, documentation)`` pair.
    ValueError
        If the format is not one `docshare` supports, or ``None``.
    """
    if not isinstance(key, tuple) or len(key) != 2:
        raise TypeError(
            f'a documentation cache key is a (format, documentation) pair, '
            f'not {key!r}; the format is None for a request that let the '
            f'format be detected'
        )
    (format, text) = key
    if format is not None and format not in SUPPORTED_FORMATS:
        raise ValueError(
            f'{format!r} is not a documentation format; expected None or '
            f'one of {", ".join(map(repr, SUPPORTED_FORMATS))}'
        )
    if text is not None and not isinstance(text, str):
        raise TypeError(
            f'the documentation half of a cache key is a string or None, '
            f'not {type(text).__name__}'
        )


class DocCache(MutableMapping):
    """A bounded cache of parsed documentation.

    The cache behaves as an ordinary mutable mapping from a
    ``(format, docstring)`` pair to the `Document` that pair parses to,
    discarding the least recently used entry when it grows past
    `DocCache.maxsize`. The format is the one that was *asked for*, so it is
    ``None`` for a request that let the format be detected.

    An instance of this class is exposed as `docshare.doccache`. It is public
    so that it can be inspected, cleared, resized, or pre-loaded, all of which
    have legitimate uses; it is nonetheless the library's own working state,
    and putting a document into it that does not correspond to its key will
    produce documentation that does not correspond to anything.

    A key is a ``(format, documentation)`` pair, and is checked on every
    access. A dictionary would accept a bare docstring as a key without
    complaint, store it, and never read it again; checking turns that into an
    error where it happens rather than a cache that is quietly wrong.

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
        _check_key(key)
        with self._lock:
            document = self._entries[key]
            self._entries.move_to_end(key)
            return document

    def __setitem__(self, key, value):
        _check_key(key)
        with self._lock:
            if self._maxsize == 0:
                return
            self._entries[key] = value
            self._entries.move_to_end(key)
            self._evict()

    def __delitem__(self, key):
        _check_key(key)
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
        _check_key(key)
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


#: The documentation `docshare` has parsed, keyed by ``(format, docstring)``.
doccache = DocCache()


def source_document(obj):
    """Return the documentation of an inheritance source.

    A source is ordinarily an object with a docstring, but an already-parsed
    `Document` may be given instead. That is how a source whose format cannot
    be detected, or which must be read as a particular one, is supplied: parse
    it with `docparse` first and hand over the result.

    Parameters
    ----------
    obj : object
        The source: a documented object, a docstring, or a `Document`.

    Returns
    -------
    Document
        The source's documentation.
    """
    if isinstance(obj, Document):
        return obj
    return docinfo(obj)


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
        return doccache[(format, text)]
    except KeyError:
        pass
    info = parse_document(text, format=format)
    doccache[(format, text)] = info
    return info


def set_docinfo(obj, info, text=None, format=None):
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
    format : str, optional
        The format `text` is written in. The record answers a request for
        that format and a request that lets the format be detected, since
        detecting the format of `text` yields the same thing.

    Returns
    -------
    None
    """
    text = documentation(obj) if text is None else text
    doccache[(None, text)] = info
    if format is not None:
        doccache[(format, text)] = info


def clear_docinfo(obj=None):
    """Forget recorded documentation.

    Parameters
    ----------
    obj : object, optional
        The object whose documentation should be forgotten, in every format
        it may have been read as. The default forgets everything, which is
        chiefly useful in tests.

    Returns
    -------
    None
    """
    if obj is None:
        doccache.clear()
        return
    text = documentation(obj)
    for format in (None, *SUPPORTED_FORMATS):
        doccache.pop((format, text), None)
