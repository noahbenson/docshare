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

from ._exceptions import (
    DocFormatError,
    DocInheritanceError,
    DocMappingError,
    DocParseError,
    DocShareError,
    DocSignatureError,
)

__version__ = '0.1.0.dev0'

__all__ = (
    'DocFormatError',
    'DocInheritanceError',
    'DocMappingError',
    'DocParseError',
    'DocShareError',
    'DocSignatureError',
    '__version__',
)
