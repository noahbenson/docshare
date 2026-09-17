# -*- coding: utf-8 -*-
"""Tests that keep the README honest.

The README documents an argument for every section and an exception for every
failure. Both are generated from the registry, so both can drift; these tests
compare the documentation against the code rather than trusting either.
"""

import pathlib
import re

import pytest

import docshare
from docshare._decorator import GENERAL_ARGUMENTS, SECTION_ARGUMENTS

README = pathlib.Path(__file__).resolve().parent.parent / 'README.md'
TEXT = README.read_text()

CODE_BLOCKS = re.findall(r'```python\n(.*?)```', TEXT, re.S)
# Only code contexts count: inline code spans and fenced blocks. Prose that
# happens to contain the word "inheritance" is not a claim about an argument.
# Inline code may carry a call after the name, as in `docparse(obj)`; the
# leading identifier is what names the API.
INLINE_CODE = set(re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)[^`]*`', TEXT)) | {
    name
    for block in re.findall(r'```python\n(.*?)```', TEXT, re.S)
    for name in re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', block)
}


def test_the_readme_exists_and_is_not_the_specification():
    assert TEXT.startswith('# `docshare`')
    assert 'Draft specification' not in TEXT


@pytest.mark.parametrize('name', sorted(SECTION_ARGUMENTS))
def test_every_section_argument_is_documented(name):
    assert name in INLINE_CODE, f'{name} is missing from the README'


@pytest.mark.parametrize('name', sorted(GENERAL_ARGUMENTS))
def test_every_general_argument_is_documented(name):
    assert name in INLINE_CODE, f'{name} is missing from the README'


@pytest.mark.parametrize(
    'name',
    sorted(n for n in INLINE_CODE if re.fullmatch(r'(inherit|drop)\w+', n)),
)
def test_no_invented_inherit_or_drop_arguments(name):
    known = set(SECTION_ARGUMENTS) | set(GENERAL_ARGUMENTS)
    assert name in known, f'the README documents {name}, which does not exist'


@pytest.mark.parametrize(
    'name', sorted(n for n in INLINE_CODE if n.endswith('map'))
)
def test_no_invented_mapping_arguments(name):
    known = set(SECTION_ARGUMENTS) | set(GENERAL_ARGUMENTS)
    assert name in known, f'the README documents {name}, which does not exist'


@pytest.mark.parametrize(
    'name',
    [
        'DocShareError',
        'DocParseError',
        'DocFormatError',
        'DocInheritanceError',
        'DocMappingError',
        'DocSignatureError',
    ],
)
def test_every_documented_exception_exists(name):
    assert name in INLINE_CODE
    assert issubclass(getattr(docshare, name), docshare.DocShareError)


@pytest.mark.parametrize('name', ['docshare', 'docparse', 'docinfo'])
def test_the_documented_public_api_exists(name):
    assert name in INLINE_CODE
    assert hasattr(docshare, name)


@pytest.mark.parametrize(
    ('index', 'block'),
    list(enumerate(CODE_BLOCKS)),
    ids=[f'block{i}' for i in range(len(CODE_BLOCKS))],
)
def test_every_code_block_is_valid_python(index, block):
    compile(block, f'README.md:block{index}', 'exec')


def test_the_quick_start_example_produces_what_the_readme_shows():
    namespace = {}
    exec(CODE_BLOCKS[0], namespace)
    expected = (
        'Returns the log of the quux of arguments `foo` and `bar`.\n'
        '\n'
        'Parameters\n'
        '----------\n'
        'foo : float\n'
        '    The foo parameter for the quux operation.\n'
        'bar : float, optional\n'
        '    The bar parameter for the quux operation; the default is 1.\n'
        'base : float, optional\n'
        '    The base of the log that should be used; the default is '
        '``None``.\n'
        '\n'
        'Returns\n'
        '-------\n'
        'float\n'
        '    The log-quux result.'
    )
    assert namespace['logquuxatize'].__doc__ == expected
    # And the README shows exactly that, in its following text block.
    assert expected in TEXT


def test_the_docparse_example_runs():
    block = next(b for b in CODE_BLOCKS if 'doc = docparse(' in b)
    exec(block, {})


def test_the_readme_does_not_promise_runtime_dependencies():
    assert 'no runtime dependencies' in TEXT


def test_the_supported_python_version_matches_the_packaging():
    pyproject = (README.parent / 'pyproject.toml').read_text()
    assert 'requires-python = ">=3.10"' in pyproject
    assert 'Python 3.10 and later' in TEXT
