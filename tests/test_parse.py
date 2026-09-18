# -*- coding: utf-8 -*-
"""Tests for the parsing engine.

The paired corpus below expresses the same documentation in both supported
formats. Every pair is asserted to produce the same semantic document, which
is the core promise of specification section 4.3.
"""

import pytest

from corpus import CORPUS, CORPUS_IDS, semantics
from docshare import DocFormatError, DocParseError, Item, section_kind
from docshare._google import parse_items as google_parse_items
from docshare._parser import parse_document


@pytest.mark.parametrize(
    ('numpy_text', 'google_text'),
    [(entry[1], entry[2]) for entry in CORPUS],
    ids=CORPUS_IDS,
)
def test_the_two_formats_agree(numpy_text, google_text):
    assert semantics(parse_document(numpy_text)) == semantics(
        parse_document(google_text)
    )


@pytest.mark.parametrize(
    ('text', 'expected'),
    [(entry[1], 'numpy') for entry in CORPUS[2:]]
    + [(entry[2], 'google') for entry in CORPUS[2:]],
)
def test_formats_are_detected(text, expected):
    assert parse_document(text).format == expected


@pytest.mark.parametrize(
    ('text', 'fmt'),
    [(entry[1], 'numpy') for entry in CORPUS]
    + [(entry[2], 'google') for entry in CORPUS],
)
def test_an_explicit_format_is_accepted_when_it_matches(text, fmt):
    assert parse_document(text, format=fmt).format == fmt


# Empty and minimal documents ################################################


@pytest.mark.parametrize('text', [None, '', '   \n  '])
def test_blank_documentation_parses_to_an_empty_document(text):
    doc = parse_document(text)
    assert doc.empty
    assert not doc
    assert doc.format is None


def test_an_explicit_format_survives_an_empty_document():
    assert parse_document(None, format='numpy').format == 'numpy'


def test_a_sectionless_document_has_no_format():
    assert parse_document('Just a summary.').format is None


# Section handling ###########################################################


def test_an_unknown_section_is_opaque_and_verbatim():
    doc = parse_document(
        'S.\n\nEfferents\n---------\nLine one.\n\nLine two.\n'
    )
    section = doc.section('Efferents')
    assert section.opaque
    assert section.items == ()
    assert section.text == ('Line one.', '', 'Line two.')


def test_a_prose_section_keeps_its_text():
    doc = parse_document('S.\n\nNotes\n-----\nProse here.\n')
    section = doc.section('notes')
    assert not section.opaque
    assert not section.structured
    assert section.text == ('Prose here.',)
    assert section.items == ()


def test_an_examples_section_is_preserved_verbatim():
    doc = parse_document(
        'S.\n\nExamples\n--------\n>>> f(1)\n2\n>>> f(2)\n4\n'
    )
    assert doc.section('examples').text == ('>>> f(1)', '2', '>>> f(2)', '4')


def test_section_names_keep_their_source_spelling():
    assert (
        parse_document('S.\n\nArgs:\n    x (int): X.\n').sections[0].name
        == 'Args'
    )
    assert (
        parse_document('S.\n\nParameters\n----------\nx : int\n')
        .sections[0]
        .name
        == 'Parameters'
    )


def test_google_keyword_args_is_its_own_section():
    doc = parse_document('S.\n\nKeyword Args:\n    x (int): The x.\n')
    assert doc.section('keyword_arguments') is not None
    assert doc.section('parameters') is None


# Item detail ################################################################


def test_a_grouped_parameter_is_one_item():
    doc = parse_document(
        'S.\n\nParameters\n----------\nx, y : float\n    C.\n'
    )
    items = doc.section('parameters').items
    assert len(items) == 1
    assert items[0].names == ('x', 'y')
    assert items[0].grouped


def test_a_type_is_kept_verbatim():
    doc = parse_document(
        'S.\n\nParameters\n----------\nx : Sequence[int], optional\n    X.\n'
    )
    assert doc.section('parameters').items[0].type == 'Sequence[int], optional'


def test_a_google_type_with_a_comma_survives():
    doc = parse_document('S.\n\nReturns:\n    dict, optional: The result.\n')
    item = doc.section('returns').items[0]
    assert item.names == ()
    assert item.type == 'dict, optional'


def test_an_unnamed_return_has_no_names():
    doc = parse_document('S.\n\nReturns\n-------\nfloat\n    The result.\n')
    assert doc.section('returns').items[0] == Item(
        names=(), type='float', description=('The result.',)
    )


def test_a_bare_parameter_is_a_name_not_a_type():
    doc = parse_document('S.\n\nParameters\n----------\nx\n    The x.\n')
    item = doc.section('parameters').items[0]
    assert item.names == ('x',)
    assert item.type is None


def test_a_bare_raises_entry_is_a_type_not_a_name():
    doc = parse_document('S.\n\nRaises\n------\nValueError\n    Bad.\n')
    item = doc.section('raises').items[0]
    assert item.names == ()
    assert item.type == 'ValueError'


def test_a_parameter_declared_with_an_empty_type():
    doc = parse_document('S.\n\nParameters\n----------\nx :\n    The x.\n')
    item = doc.section('parameters').items[0]
    assert item.names == ('x',)
    assert item.type is None


def test_a_google_returns_section_may_be_bare_prose():
    doc = parse_document('S.\n\nReturns:\n    The computed result.\n')
    items = doc.section('returns').items
    assert len(items) == 1
    assert items[0].names == ()
    assert items[0].type is None
    assert items[0].description == ('The computed result.',)


def test_item_order_is_preserved():
    doc = parse_document(
        'S.\n\nParameters\n----------\nc : int\n    C.\na : int\n    A.\n'
    )
    assert [i.name for i in doc.section('parameters').items] == ['c', 'a']


def test_an_item_may_have_no_description():
    doc = parse_document('S.\n\nParameters\n----------\nx : int\ny : int\n')
    items = doc.section('parameters').items
    assert [i.name for i in items] == ['x', 'y']
    assert items[0].description == ()


def test_an_empty_google_body_yields_no_items():
    # The lexer never produces this, since a Google header requires an
    # indented body; the item parser must still cope with it.
    assert google_parse_items((), section_kind('parameters')) == ((), ())


# Errors #####################################################################


def test_a_mixed_document_is_rejected():
    text = 'S.\n\nParameters\n----------\nx : int\n\nReturns:\n    int\n'
    with pytest.raises(DocFormatError, match='mixes'):
        parse_document(text)


def test_a_document_may_not_be_parsed_as_the_wrong_format():
    with pytest.raises(DocFormatError, match='required to be'):
        parse_document('S.\n\nArgs:\n    x (int): X.\n', format='numpy')


def test_a_google_document_may_not_be_parsed_as_numpy():
    with pytest.raises(DocFormatError, match='no numpy sections'):
        parse_document('S.\n\nArgs:\n    x (int): X.\n', format='numpy')


def test_a_numpy_document_may_not_be_parsed_as_google():
    with pytest.raises(DocFormatError, match='no google sections'):
        parse_document(
            'S.\n\nParameters\n----------\nx : int\n', format='google'
        )


def test_a_sectionless_document_accepts_either_explicit_format():
    for fmt in ('numpy', 'google'):
        assert parse_document('Just a summary.', format=fmt).format == fmt


def test_an_unsupported_format_is_rejected():
    with pytest.raises(DocFormatError, match='unsupported'):
        parse_document('S.', format='rest')


def test_an_empty_numpy_type_is_not_read_as_a_google_section():
    doc = parse_document('S.\n\nParameters\n----------\nx :\n    The x.\n')
    assert doc.format == 'numpy'
    assert doc.section('parameters').items[0].names == ('x',)


def test_a_parameter_named_like_a_section_needs_an_explicit_format():
    # `notes :` is a parameter with no type, but it also has the shape of a
    # Google `Notes:` header, so automatic detection cannot tell.
    text = 'S.\n\nParameters\n----------\nnotes :\n    Some notes.\n'
    with pytest.raises(DocFormatError, match='mixes'):
        parse_document(text)
    # An explicit format is the documented way out.
    doc = parse_document(text, format='numpy')
    assert doc.section('parameters').items[0].names == ('notes',)


def test_the_ambiguity_error_suggests_an_explicit_format():
    text = 'S.\n\nParameters\n----------\nnotes :\n    Some notes.\n'
    with pytest.raises(DocFormatError) as info:
        parse_document(text)
    assert 'format=' in str(info.value)


def test_prose_in_a_google_parameter_section_is_prose_not_an_error():
    # A line that declares nothing is a description of the section.
    doc = parse_document('S.\n\nArgs:\n    just some prose\n')
    section = doc.section('parameters')
    assert section.text == ('just some prose',)
    assert section.items == ()


def test_an_unparseable_google_parameter_is_an_error():
    # A bare name is a declaration in NumPy style but not in Google style,
    # where an item always carries a colon.
    with pytest.raises(DocParseError, match='Args'):
        parse_document('S.\n\nArgs:\n    x\n')


def test_the_google_parse_error_shows_the_offending_line():
    with pytest.raises(DocParseError) as info:
        parse_document('S.\n\nArgs:\n    x\n')
    assert "'x'" in str(info.value)


def test_prose_does_not_excuse_a_malformed_declaration_after_it():
    with pytest.raises(DocParseError, match='Args'):
        parse_document('S.\n\nArgs:\n    A note.\n\n    x\n')


def test_a_later_unparseable_google_item_is_an_error():
    text = 'S.\n\nArgs:\n    x (int): The x.\n    nonsense here\n'
    with pytest.raises(DocParseError, match='nonsense here'):
        parse_document(text)
