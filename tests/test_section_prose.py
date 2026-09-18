# -*- coding: utf-8 -*-
"""Tests for prose that introduces a structured section.

Specification section 31 asks that section descriptions be preserved. A
structured section may open with prose about the section as a whole before
its items begin; telling that apart from an item is syntactic rather than a
guess, and only possible where items are named.
"""

import pytest

from docshare import DocParseError, clear_docinfo, docparse, docwrap
from docshare._lex import is_declaration, split_prose
from docshare._render import render_document

NUMPY = (
    'Do a thing.\n'
    '\n'
    'Parameters\n'
    '----------\n'
    'All of these are optional.\n'
    '\n'
    'x : int\n'
    '    The x.\n'
)
GOOGLE = (
    'Do a thing.\n'
    '\n'
    'Args:\n'
    '    All of these are optional.\n'
    '\n'
    '    x (int): The x.\n'
)


@pytest.fixture(autouse=True)
def _empty_cache():
    clear_docinfo()
    yield
    clear_docinfo()


# The declaration test #######################################################


@pytest.mark.parametrize(
    'line',
    [
        'x : int',
        'x, y : float',
        'n_components : int, optional',
        'x',
        'value',
        'x, y',
        '*args',
        '**kwargs',
        'ValueError',
        'float',
    ],
)
def test_declarations_are_recognized(line):
    assert is_declaration(line)


@pytest.mark.parametrize(
    'line',
    [
        'All of these are optional.',
        'These are all read-only.',
        'Parameters are passed to foo.',
        'See the notes below.',
        'array_like of int',
        '',
        '   ',
    ],
)
def test_prose_is_recognized(line):
    assert not is_declaration(line)


def test_a_bare_identifier_reads_as_a_declaration():
    # Genuinely ambiguous to a human reader too; documented as such.
    assert is_declaration('None')


# Splitting ##################################################################


def test_split_prose_separates_a_leading_block():
    (prose, rest) = split_prose(('A note.', '', 'x : int', '    The x.'))
    assert prose == ('A note.',)
    assert rest == ('x : int', '    The x.')


def test_split_prose_of_a_body_with_no_prose():
    (prose, rest) = split_prose(('x : int', '    The x.'))
    assert prose == ()
    assert rest == ('x : int', '    The x.')


def test_split_prose_of_a_body_that_is_all_prose():
    (prose, rest) = split_prose(('A note.', 'And more.'))
    assert prose == ('A note.', 'And more.')
    assert rest == ()


def test_split_prose_of_an_empty_body():
    assert split_prose(()) == ((), ())


def test_split_prose_of_a_blank_body():
    assert split_prose(('', '   ')) == ((), ('', '   '))


def test_split_prose_ignores_indented_lines_when_looking():
    # An indented first line belongs to nothing yet; the scan passes over it.
    (_, rest) = split_prose(('    orphan', 'x : int'))
    assert rest[-1] == 'x : int'


def test_split_prose_spans_several_lines_and_blanks():
    (prose, rest) = split_prose(('One.', '', 'Two.', '', 'x : int'))
    assert prose == ('One.', '', 'Two.')
    assert rest == ('x : int',)


# Parsing ####################################################################


@pytest.mark.parametrize('text', [NUMPY, GOOGLE], ids=['numpy', 'google'])
def test_prose_is_parsed_onto_the_section(text):
    section = docparse(text).section('parameters')
    assert section.text == ('All of these are optional.',)
    assert [item.names for item in section.items] == [('x',)]


@pytest.mark.parametrize('text', [NUMPY, GOOGLE], ids=['numpy', 'google'])
def test_prose_does_not_become_an_item(text):
    section = docparse(text).section('parameters')
    assert len(section.items) == 1


def test_attributes_may_carry_prose():
    doc = docparse(
        'S.\n\nAttributes\n----------\nRead-only.\n\nvalue : int\n    V.\n'
    )
    section = doc.section('attributes')
    assert section.text == ('Read-only.',)
    assert [item.names for item in section.items] == [('value',)]


def test_a_section_may_be_prose_alone():
    doc = docparse(
        'S.\n\nParameters\n----------\nEverything is passed to foo.\n'
    )
    section = doc.section('parameters')
    assert section.text == ('Everything is passed to foo.',)
    assert section.items == ()


# Sections identified by position keep their free-text types #################


def test_a_numpy_return_type_is_not_read_as_prose():
    # A bare line in Returns is a type, and a type is free text.
    doc = docparse(
        'S.\n\nReturns\n-------\narray_like of int\n    The values.\n'
    )
    section = doc.section('returns')
    assert section.text == ()
    assert section.items[0].type == 'array_like of int'


def test_a_google_bare_returns_body_is_still_one_item():
    doc = docparse('S.\n\nReturns:\n    The computed result.\n')
    section = doc.section('returns')
    assert section.text == ()
    assert section.items[0].description == ('The computed result.',)


def test_a_raises_type_is_not_read_as_prose():
    doc = docparse(
        'S.\n\nRaises\n------\nValueError or TypeError\n    If bad.\n'
    )
    assert doc.section('raises').text == ()
    assert doc.section('raises').items[0].type == 'ValueError or TypeError'


# Rendering ##################################################################


@pytest.mark.parametrize('text', [NUMPY, GOOGLE], ids=['numpy', 'google'])
def test_prose_round_trips_exactly(text):
    assert render_document(docparse(text)) == text.rstrip()


def test_prose_survives_conversion_to_google():
    assert render_document(docparse(NUMPY), format='google') == GOOGLE.rstrip()


def test_prose_survives_conversion_to_numpy():
    assert render_document(docparse(GOOGLE), format='numpy') == NUMPY.rstrip()


def test_prose_alone_renders_without_a_trailing_blank_line():
    doc = docparse('S.\n\nParameters\n----------\nAll passed to foo.\n')
    assert render_document(doc) == (
        'S.\n\nParameters\n----------\nAll passed to foo.'
    )


def test_prose_alone_renders_in_google_too():
    doc = docparse('S.\n\nArgs:\n    All passed to foo.\n')
    assert render_document(doc) == 'S.\n\nArgs:\n    All passed to foo.'


def test_a_blank_line_separates_prose_from_the_items():
    out = render_document(docparse(NUMPY))
    assert 'All of these are optional.\n\nx : int' in out


# Composition ################################################################


def source(x, y):
    """Source.

    Parameters
    ----------
    Prose belonging to the source.

    x : float
        The x from source.
    y : float
        The y from source.
    """


def test_the_targets_own_section_prose_survives_composition():
    @docwrap(format='numpy', inheritparams=source)
    def target(x, y):
        """T.

        Parameters
        ----------
        My own section prose.

        y : float
            My own y.
        """

    assert 'My own section prose.' in target.__doc__
    assert 'Prose belonging to the source.' not in target.__doc__


def test_section_prose_is_not_inherited():
    # Prose describes the source's parameters, not the target's.
    @docwrap(format='numpy', inheritparams=source)
    def target(x, y):
        """T."""

    assert 'Prose belonging to the source.' not in target.__doc__
    assert 'The x from source.' in target.__doc__


def test_prose_stays_ahead_of_inherited_items():
    @docwrap(format='numpy', inheritparams=source)
    def target(x, y):
        """T.

        Parameters
        ----------
        Mine.

        y : float
            My own y.
        """

    body = target.__doc__
    assert body.index('Mine.') < body.index('x : float')


# Errors #####################################################################


def test_prose_does_not_excuse_a_malformed_google_declaration():
    with pytest.raises(DocParseError):
        docparse('S.\n\nArgs:\n    A note.\n\n    x\n')


def test_phantom_parameters_no_longer_come_from_prose():
    # This used to report a parameter named after the sentence.
    @docwrap(format='numpy')
    def target(x):
        """T.

        Parameters
        ----------
        All of these are optional.

        x : int
            The x.
        """

    assert target.__doc__ is not None
