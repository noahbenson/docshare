# -*- coding: utf-8 -*-
"""Tests that keep the documentation honest.

The README and the documentation site describe an argument for every section
and an exception for every failure. Both are generated from the section
registry, so both can drift; these tests compare what is written against what
exists rather than trusting either.

The record of deferred cases and the changelog are excluded from the drift
checks. They are historical documents that quote argument names as they were
at the time, which is the point of keeping them.
"""

import os
import pathlib
import re
import subprocess
import sys

import pytest

import docshare
from docshare import DocShareError
from docshare._decorator import (
    GENERAL_ARGUMENTS,
    SECTION_ARGUMENTS,
    custom_arguments,
)
from docshare._sections import normalize_custom

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
README = ROOT / 'README.md'

#: The documents that describe how to use the library now.
INSTRUCTIONAL = sorted(
    path
    for path in [README, *DOCS.rglob('*.md')]
    if path.name not in {'deferred.md', 'changelog.md'}
)

TEXT = '\n'.join(path.read_text() for path in INSTRUCTIONAL)

CODE_BLOCKS = [
    (path, index, block)
    for path in INSTRUCTIONAL
    for index, block in enumerate(
        re.findall(r'```python\n(.*?)```', path.read_text(), re.S)
    )
]

# Only code contexts count: inline code spans and fenced blocks. Prose that
# happens to contain the word "inheritance" is not a claim about an argument.
# A {doc} or {ref} role names a page rather than an object, so those are
# removed before the scan; a {py:...} role does name an object and stays.
_WITHOUT_ROLES = re.sub(r'\{(?:doc|ref)\}`[^`]*`', '', TEXT)
NAMED = (
    # The leading identifier of an inline code span: `docparse(obj)`.
    set(re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)[^`]*`', _WITHOUT_ROLES))
    # The final component of a dotted name: `docshare.DocParseError`.
    | set(re.findall(r'`~?[\w.]*?([A-Za-z_][A-Za-z0-9_]*)`', _WITHOUT_ROLES))
    | {
        name
        for (_, _, block) in CODE_BLOCKS
        for name in re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', block)
    }
)

#: Arguments the documentation names in order to say that they do not exist.
#: Each is the wrong half of the drop/ignore pair for its section.
DELIBERATELY_ABSENT = {'ignoreparams', 'dropreturns'}


def _declared_titles():
    """Return every section title the documentation declares with custom=.

    A declared section adds arguments generated from its title, so a page
    that declares one may legitimately name arguments that no static table
    holds. Only the titles the documentation itself declares count, so an
    argument invented out of nowhere is still caught.
    """
    titles = set()
    for literal in re.findall(r'custom=[\[{]([^\]}]*)[\]}]', TEXT):
        if ':' in literal:
            # A mapping: the titles are its keys, not the sections they
            # resemble.
            titles.update(re.findall(r"'([^']+)'\s*:", literal))
        else:
            titles.update(re.findall(r"'([^']+)'", literal))
    return titles


#: The arguments that the declarations in the documentation generate. A
#: declaration is tried against both a structured section and a prose one,
#: since the page may declare either and the arguments differ.
GENERATED = set()
for _title in _declared_titles():
    for _like in ('Parameters', 'Notes'):
        try:
            GENERATED |= set(
                custom_arguments(normalize_custom({_title: _like}))
            )
        except DocShareError:
            # A title the documentation names in order to show that it is
            # refused, or one whose arguments would collide.
            continue

#: Every argument a documented call may legitimately use.
KNOWN_ARGUMENTS = set(SECTION_ARGUMENTS) | set(GENERAL_ARGUMENTS) | GENERATED


def test_the_documentation_exists():
    assert INSTRUCTIONAL
    assert (DOCS / 'index.md').is_file()
    assert (DOCS / 'conf.py').is_file()


# The README is a summary #####################################################


def test_the_readme_is_short():
    # The detail belongs on the site; the README introduces and points there.
    assert len(README.read_text().splitlines()) < 200


def test_the_readme_links_to_the_site():
    body = README.read_text()
    assert 'noahbenson.github.io/docshare' in body
    assert '**[Read the documentation]' in body


def test_the_readme_still_shows_the_guiding_example():
    body = README.read_text()
    assert 'docwrap' in body
    assert 'inheritparams=quuxatize' in body


# Arguments ###################################################################


@pytest.mark.parametrize('name', sorted(SECTION_ARGUMENTS))
def test_every_section_argument_is_documented(name):
    assert name in NAMED, f'{name} is missing from the documentation'


@pytest.mark.parametrize('name', sorted(GENERAL_ARGUMENTS))
def test_every_general_argument_is_documented(name):
    assert name in NAMED, f'{name} is missing from the documentation'


@pytest.mark.parametrize(
    'name',
    sorted(
        n
        for n in NAMED
        if re.fullmatch(r'(inherit|drop|ignore)\w+', n)
        and n not in DELIBERATELY_ABSENT
    ),
)
def test_no_invented_inherit_or_exclude_arguments(name):
    assert name in KNOWN_ARGUMENTS, (
        f'the documentation names {name}, which does not exist'
    )


def test_the_drift_guard_still_catches_an_invented_argument():
    # The known set grows with what the documentation declares, so it is
    # worth checking that it has not grown into accepting anything.
    assert 'inheritnonsense' not in KNOWN_ARGUMENTS
    assert 'nonsensemap' not in KNOWN_ARGUMENTS


@pytest.mark.parametrize('name', sorted(DELIBERATELY_ABSENT))
def test_the_arguments_said_not_to_exist_really_do_not(name):
    # The guide names these in order to say they do not exist. If one ever
    # does, the guide is wrong; if one stops being mentioned, this list is.
    assert name not in SECTION_ARGUMENTS
    assert name not in GENERAL_ARGUMENTS
    assert name in NAMED


@pytest.mark.parametrize('name', sorted(n for n in NAMED if n.endswith('map')))
def test_no_invented_mapping_arguments(name):
    assert name in KNOWN_ARGUMENTS, (
        f'the documentation names {name}, which does not exist'
    )


def test_the_section_table_lists_every_section():
    from docshare._sections import iter_section_kinds

    table = (DOCS / 'guide' / 'sections.md').read_text()
    for kind in iter_section_kinds():
        assert f'inherit{_short(kind.name)}' in table


def _short(kind_name):
    from docshare._decorator import _short as short

    return short(kind_name)


# The public API ##############################################################


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
    assert name in NAMED
    assert issubclass(getattr(docshare, name), docshare.DocShareError)


@pytest.mark.parametrize(
    'name',
    [
        'docwrap',
        'doccompose',
        'docrender',
        'docparse',
        'docinfo',
        'doccache',
        'clear_docinfo',
    ],
)
def test_the_documented_public_api_exists(name):
    assert name in NAMED
    assert hasattr(docshare, name)


def test_the_api_reference_covers_the_public_names():
    reference = (DOCS / 'api.md').read_text()
    for name in docshare.__all__:
        if name == '__version__':
            continue
        assert name in reference, f'{name} is missing from the API reference'


# Code blocks #################################################################


@pytest.mark.parametrize(
    ('path', 'index', 'block'),
    CODE_BLOCKS,
    ids=[f'{p.name}:{i}' for (p, i, _) in CODE_BLOCKS],
)
def test_every_code_block_is_valid_python(path, index, block):
    compile(block, f'{path.name}:block{index}', 'exec')


@pytest.mark.parametrize(
    'path', INSTRUCTIONAL, ids=[p.name for p in INSTRUCTIONAL]
)
def test_every_code_block_runs(path):
    """Run a page's examples in order, as a reader would.

    The blocks of one page share a namespace, so a page may set its sources
    up once and use them afterwards, which is how the pages are written. A
    block that needs a library which is not installed is skipped rather than
    failed; the comparison with docrep is the only one.
    """
    blocks = re.findall(r'```python\n(.*?)```', path.read_text(), re.S)
    if not blocks:
        pytest.skip('no examples on this page')
    namespace = {}
    ran = 0
    for index, block in enumerate(blocks):
        try:
            exec(block, namespace)
        except ImportError as error:
            pytest.skip(f'{path.name} block {index} needs {error.name}')
        except Exception as error:
            raise AssertionError(
                f'{path.name} block {index} failed: '
                f'{type(error).__name__}: {error}'
            ) from error
        ran += 1
    assert ran == len(blocks)


def _block_containing(needle):
    for _, _, block in CODE_BLOCKS:
        if needle in block:
            return block
    raise AssertionError(f'no code block contains {needle!r}')


def test_the_quickstart_example_produces_what_is_shown():
    # The page runs its own example and then shows the result. The two must
    # agree, and that is checked against the page rather than against a copy
    # of it here, so the page cannot drift from what it demonstrates.
    page = (DOCS / 'quickstart.md').read_text()
    block = next(
        b
        for b in re.findall(r'```python\n(.*?)```', page, re.S)
        if 'def logquuxatize' in b
    )
    shown = next(
        b
        for b in re.findall(r'```text\n(.*?)```', page, re.S)
        if b.startswith('Returns the log of the quux')
    )
    namespace = {}
    exec(block, namespace)
    assert namespace['logquuxatize'].__doc__ == shown.rstrip('\n')


def test_the_docparse_example_runs():
    exec(_block_containing('doc = docparse('), {})


def test_the_numpy_example_runs():
    pytest.importorskip('numpy', reason='needs the test extra')
    exec(_block_containing('inheritparams=numpy.sum'), {})


def test_the_bare_decorator_example_runs():
    exec(_block_containing('def area(width, height)'), {})


# Consistency with the packaging ##############################################


def test_the_supported_python_version_matches_the_packaging():
    pyproject = (ROOT / 'pyproject.toml').read_text()
    assert 'requires-python = ">=3.10"' in pyproject
    assert 'Python 3.10 and later' in TEXT


def test_the_documentation_promises_no_runtime_dependencies():
    assert 'no runtime dependencies' in TEXT.lower()
    pyproject = (ROOT / 'pyproject.toml').read_text()
    assert 'dependencies = []' in pyproject


# The site builds #############################################################


def test_the_site_builds_without_warnings(tmp_path):
    pytest.importorskip('sphinx', reason='needs the docs extra')
    pytest.importorskip('myst_parser', reason='needs the docs extra')
    pytest.importorskip('furo', reason='needs the docs extra')
    environment = dict(os.environ, DOCSHARE_DOCS_OFFLINE='1')
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'sphinx',
            '-b',
            'html',
            '-W',
            '--keep-going',
            '-q',
            str(DOCS),
            str(tmp_path / 'html'),
        ],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert (tmp_path / 'html' / 'index.html').is_file()
    assert (tmp_path / 'html' / 'api.html').is_file()
