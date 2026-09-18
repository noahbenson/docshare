# -*- coding: utf-8 -*-
################################################################################
# docshare/__init__.py

"""Parse, compose, and selectively inherit structured Python documentation.

`docshare` is a small, pure-Python library that eliminates repetitive
documentation between related functions, methods, and classes while leaving
ordinary Python docstrings as the final documentation source consumed by
`help()`, IDEs, and documentation generators such as Sphinx.

The core API consists of the `docshare` decorator, which composes documentation
at decoration time, along with `docparse` and `docinfo`, which respectively
parse and cache the semantic representation of an object's documentation.
"""

from ._cache import (
    DocCache,
    clear_docinfo,
    doccache,
    docinfo,
    docparse,
)
from ._decorator import docwrap
from ._exceptions import (
    DocFormatError,
    DocInheritanceError,
    DocMappingError,
    DocParseError,
    DocShareError,
    DocSignatureError,
)
from ._model import Document, FrozenDict, Item, Section
from ._sections import SUPPORTED_FORMATS, SectionKind, section_kind

__version__ = '0.2.0'

__all__ = (
    'SUPPORTED_FORMATS',
    'DocCache',
    'DocFormatError',
    'DocInheritanceError',
    'DocMappingError',
    'DocParseError',
    'DocShareError',
    'DocSignatureError',
    'Document',
    'FrozenDict',
    'Item',
    'Section',
    'SectionKind',
    '__version__',
    'clear_docinfo',
    'doccache',
    'docinfo',
    'docparse',
    'docwrap',
    'section_kind',
)
