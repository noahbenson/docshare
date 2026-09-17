# -*- coding: utf-8 -*-
"""Smoke tests: the package imports and exposes its public surface."""

import importlib
import re

import pytest

import docshare


def test_version_is_pep440():
    assert isinstance(docshare.__version__, str)
    assert re.match(r'^\d+\.\d+\.\d+', docshare.__version__)


def test_all_names_are_importable():
    for name in docshare.__all__:
        assert hasattr(docshare, name), f'{name} missing from docshare'


@pytest.mark.parametrize(
    'name',
    [
        'DocParseError',
        'DocFormatError',
        'DocInheritanceError',
        'DocMappingError',
        'DocSignatureError',
    ],
)
def test_exceptions_derive_from_base(name):
    exc = getattr(docshare, name)
    assert issubclass(exc, docshare.DocShareError)
    assert issubclass(exc, Exception)


def test_base_exception_is_not_bare_exception():
    assert docshare.DocShareError is not Exception
    assert issubclass(docshare.DocShareError, Exception)


def test_exceptions_module_all_matches_definitions():
    mod = importlib.import_module('docshare._exceptions')
    for name in mod.__all__:
        assert hasattr(mod, name)


def test_package_is_typed():
    # PEP 561: the marker file must ship with the package.
    import pathlib

    root = pathlib.Path(docshare.__file__).parent
    assert (root / 'py.typed').is_file()
