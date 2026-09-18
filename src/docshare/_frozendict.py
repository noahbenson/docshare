# -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
## -*- coding: utf-8 -*-
#
# docshare/_frozendict.py
#
# The immutable, hashable mapping used throughout the library.

"""An immutable, hashable mapping.

This lives on its own because both the section registry and the document
model need it, and the model is built on the registry. Every record in
`docshare` is immutable and hashable as a whole, which is what makes a
cached document safe to share between objects; a record holding an
ordinary mapping would be neither.
"""

from __future__ import annotations

from collections.abc import Mapping

__all__ = ('FrozenDict',)


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
