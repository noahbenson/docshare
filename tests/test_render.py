# -*- coding: utf-8 -*-
"""Tests for rendering a document back into docstring text."""

import pytest

from corpus import CORPUS, CORPUS_IDS, semantics
from docshare import DocFormatError, Document, Item, Section
from docshare._parser import parse_document
from docshare._render import render_document

NUMPY_CASES = [(entry[0], entry[1]) for entry in CORPUS]
GOOGLE_CASES = [(entry[0], entry[2]) for entry in CORPUS]


# Round trips ################################################################


@pytest.mark.parametrize(
    'text', [entry[1] for entry in CORPUS], ids=CORPUS_IDS
)
def test_numpy_round_trip_preserves_meaning(text):
    original = parse_document(text)
    again = parse_document(render_document(original))
    assert semantics(again) == semantics(original)


@pytest.mark.parametrize(
    'text', [entry[2] for entry in CORPUS], ids=CORPUS_IDS
)
def test_google_round_trip_preserves_meaning(text):
    original = parse_document(text)
    again = parse_document(render_document(original))
    assert semantics(again) == semantics(original)


@pytest.mark.parametrize(
    'text', [entry[1] for entry in CORPUS], ids=CORPUS_IDS
)
def test_numpy_round_trip_is_idempotent(text):
    once = render_document(parse_document(text))
    twice = render_document(parse_document(once))
    assert once == twice


@pytest.mark.parametrize(
    'text', [entry[2] for entry in CORPUS], ids=CORPUS_IDS
)
def test_google_round_trip_is_idempotent(text):
    once = render_document(parse_document(text))
    twice = render_document(parse_document(once))
    assert once == twice


@pytest.mark.parametrize(
    'text', [entry[1] for entry in CORPUS], ids=CORPUS_IDS
)
def test_numpy_converts_into_google_without_loss(text):
    original = parse_document(text)
    converted = parse_document(render_document(original, format='google'))
    assert semantics(converted) == semantics(original)
    assert converted.format in ('google', None)


@pytest.mark.parametrize(
    'text', [entry[2] for entry in CORPUS], ids=CORPUS_IDS
)
def test_google_converts_into_numpy_without_loss(text):
    original = parse_document(text)
    converted = parse_document(render_document(original, format='numpy'))
    assert semantics(converted) == semantics(original)


@pytest.mark.parametrize(
    ('numpy_text', 'google_text'),
    [(entry[1], entry[2]) for entry in CORPUS],
    ids=CORPUS_IDS,
)
def test_conversion_reproduces_the_other_spelling(numpy_text, google_text):
    # Converting either way produces documentation that parses the same as
    # the hand-written version in the target format.
    as_google = render_document(parse_document(numpy_text), format='google')
    assert semantics(parse_document(as_google)) == semantics(
        parse_document(google_text)
    )
    as_numpy = render_document(parse_document(google_text), format='numpy')
    assert semantics(parse_document(as_numpy)) == semantics(
        parse_document(numpy_text)
    )


# Exact output ###############################################################


def test_numpy_output_is_byte_identical_for_canonical_input():
    text = (
        'Compute a quux.\n'
        '\n'
        'Longer prose.\n'
        '\n'
        'Parameters\n'
        '----------\n'
        'x, y : float\n'
        '    Cartesian coordinates.\n'
        'scale : int, optional\n'
        '    The scale.\n'
        '\n'
        'Returns\n'
        '-------\n'
        'float\n'
        '    The result.\n'
        '\n'
        'Efferents\n'
        '---------\n'
        'Downstream connections.'
    )
    assert render_document(parse_document(text)) == text


def test_google_output_is_byte_identical_for_canonical_input():
    text = (
        'Compute a quux.\n'
        '\n'
        'Longer prose.\n'
        '\n'
        'Args:\n'
        '    x, y (float): Cartesian coordinates.\n'
        '    scale (int, optional): The scale.\n'
        '\n'
        'Returns:\n'
        '    float: The result.\n'
        '\n'
        'Efferents:\n'
        '    Downstream connections.'
    )
    assert render_document(parse_document(text)) == text


def test_underlines_match_their_titles():
    out = render_document(parse_document('S.\n\nSee Also\n--------\nx\n'))
    assert 'See Also\n--------' in out


def test_a_grouped_declaration_stays_on_one_line():
    doc = parse_document(
        'S.\n\nParameters\n----------\nx, y : float\n    Coordinates.\n'
    )
    assert 'x, y : float' in render_document(doc)
    assert 'x, y (float):' in render_document(doc, format='google')


def test_multiline_descriptions_are_indented():
    doc = parse_document(
        'S.\n\nParameters\n----------\nx : int\n    One.\n    Two.\n'
    )
    assert render_document(doc).endswith('x : int\n    One.\n    Two.')
    assert render_document(doc, format='google').endswith(
        'Args:\n    x (int): One.\n        Two.'
    )


def test_section_titles_take_their_canonical_spelling():
    doc = parse_document('S.\n\nArguments:\n    x (int): The x.\n')
    assert 'Args:' in render_document(doc)
    assert 'Parameters\n----------' in render_document(doc, format='numpy')


def test_sections_are_separated_by_one_blank_line():
    doc = parse_document(
        'S.\n\nParameters\n----------\nx : int\n\nNotes\n-----\nA.\n'
    )
    assert '\n\nNotes\n' in render_document(doc)
    assert '\n\n\n' not in render_document(doc)


def test_opaque_section_text_is_reproduced_verbatim():
    text = 'S.\n\nEfferents\n---------\nLine one.\n\nLine two.\n'
    out = render_document(parse_document(text))
    assert out.endswith('Efferents\n---------\nLine one.\n\nLine two.')


def test_section_order_is_preserved():
    text = 'S.\n\nReturns\n-------\nint\n\nParameters\n----------\nx : int\n'
    out = render_document(parse_document(text))
    assert out.index('Returns') < out.index('Parameters')


# Keyword arguments ##########################################################


def test_google_keyword_args_merge_into_numpy_parameters():
    doc = parse_document(
        'S.\n\n'
        'Args:\n    x (int): The x.\n\n'
        'Keyword Args:\n    flag (bool): A flag.\n'
    )
    out = render_document(doc, format='numpy')
    assert out.count('Parameters') == 1
    assert 'Keyword' not in out
    parameters = parse_document(out).section('parameters')
    assert [i.name for i in parameters.items] == ['x', 'flag']


def test_google_keyword_args_stay_separate_in_google():
    doc = parse_document(
        'S.\n\n'
        'Args:\n    x (int): The x.\n\n'
        'Keyword Args:\n    flag (bool): A flag.\n'
    )
    out = render_document(doc, format='google')
    assert 'Args:' in out
    assert 'Keyword Args:' in out


def test_keyword_args_alone_still_render_as_numpy_parameters():
    doc = parse_document('S.\n\nKeyword Args:\n    flag (bool): A flag.\n')
    out = render_document(doc, format='numpy')
    assert 'Parameters\n----------' in out
    assert parse_document(out).section('parameters').items[0].name == 'flag'


def test_keyword_args_before_args_still_merge_once():
    doc = parse_document(
        'S.\n\n'
        'Keyword Args:\n    flag (bool): A flag.\n\n'
        'Args:\n    x (int): The x.\n'
    )
    out = render_document(doc, format='numpy')
    assert out.count('Parameters\n----------') == 1
    names = [i.name for i in parse_document(out).section('parameters').items]
    assert names == ['flag', 'x']


# Documents that did not come from a docstring ###############################


def test_an_empty_document_renders_to_nothing():
    assert render_document(Document()) == ''


def test_a_summary_only_document_needs_no_format():
    # Nothing in such a document is format-specific.
    assert render_document(Document(summary='Do a thing.')) == 'Do a thing.'


def test_a_description_without_a_summary():
    doc = Document(description=('One.', 'Two.'))
    assert render_document(doc) == 'One.\nTwo.'


def test_a_document_with_sections_and_no_format_is_an_error():
    doc = Document(
        summary='S.',
        sections=[Section(name='Notes', kind='notes', text=('A note.',))],
    )
    with pytest.raises(DocFormatError, match='no format is known'):
        render_document(doc)


def test_an_explicit_format_renders_a_formatless_document():
    doc = Document(
        summary='S.',
        sections=[Section(name='Notes', kind='notes', text=('A note.',))],
    )
    assert render_document(doc, format='numpy').endswith(
        'Notes\n-----\nA note.'
    )


def test_an_unsupported_format_is_rejected():
    with pytest.raises(DocFormatError, match='unsupported'):
        render_document(Document(summary='S.'), format='rest')


def test_an_explicit_format_overrides_the_documents_own():
    doc = parse_document('S.\n\nNotes\n-----\nA.\n')
    assert doc.format == 'numpy'
    assert 'Notes:' in render_document(doc, format='google')


# Item shapes ################################################################


def test_an_item_with_no_description():
    doc = Document(
        sections=[
            Section(
                name='Parameters',
                kind='parameters',
                items=[Item(names='x', type='int')],
            )
        ],
        format='numpy',
    )
    assert render_document(doc) == 'Parameters\n----------\nx : int'


def test_an_item_with_neither_a_name_nor_a_type_nor_a_description():
    doc = Document(
        sections=[Section(name='Returns', kind='returns', items=[Item()])],
        format='numpy',
    )
    # Nothing to write, so the section is empty but still present.
    assert render_document(doc) == 'Returns\n-------'


def test_an_empty_section_survives_numpy_but_not_google():
    doc = Document(
        sections=[Section(name='Notes', kind='notes')], format='numpy'
    )
    assert render_document(doc) == 'Notes\n-----'
    # A Google header is only a header when an indented body follows, so an
    # empty section cannot be expressed; see docs/deferred.md.
    assert render_document(doc, format='google') == ''


def test_a_bare_google_returns_item_round_trips_within_google():
    doc = parse_document('S.\n\nReturns:\n    The computed result.\n')
    again = parse_document(render_document(doc))
    assert semantics(again) == semantics(doc)


def test_a_bare_google_returns_item_becomes_a_type_in_numpy():
    # NumPy has no way to write a return with a description but no type, so
    # the description becomes the declaration line; see docs/deferred.md.
    doc = parse_document('S.\n\nReturns:\n    The computed result.\n')
    converted = parse_document(render_document(doc, format='numpy'))
    item = converted.section('returns').items[0]
    assert item.type == 'The computed result.'
    assert item.description == ()
