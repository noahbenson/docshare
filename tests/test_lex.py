# -*- coding: utf-8 -*-
"""Tests for the format-independent section lexer."""

import pytest

from docshare import DocFormatError
from docshare._lex import clean, detect_format, iter_blocks, lex

# clean ######################################################################


@pytest.mark.parametrize('text', [None, '', '   ', '\n\n', '\t\n  \n'])
def test_clean_of_blank_documentation_is_empty(text):
    assert clean(text) == []


def test_clean_strips_the_python_indentation():
    text = """Summary.

        Indented body.
        """
    assert clean(text) == ['Summary.', '', 'Indented body.']


def test_clean_preserves_relative_indentation():
    text = 'Summary.\n\n    Deeper.\n        Deeper still.\n'
    assert clean(text) == [
        'Summary.',
        '',
        'Deeper.',
        '    Deeper still.',
    ]


# Structure ##################################################################


def test_empty_document_lexes_to_nothing():
    lexed = lex(None)
    assert lexed.summary is None
    assert lexed.description == ()
    assert lexed.sections == ()
    assert lexed.styles == frozenset()


def test_summary_only_document():
    lexed = lex('Do a thing.')
    assert lexed.summary == 'Do a thing.'
    assert lexed.description == ()
    assert lexed.sections == ()


def test_multiline_summary_is_one_paragraph():
    lexed = lex('Do a thing\nthat spans lines.\n\nThen prose.')
    assert lexed.summary == 'Do a thing\nthat spans lines.'
    assert lexed.description == ('Then prose.',)


def test_description_keeps_its_blank_lines():
    lexed = lex('Summary.\n\nOne.\n\nTwo.\n')
    assert lexed.description == ('One.', '', 'Two.')


def test_document_with_no_summary_but_a_section():
    lexed = lex('Parameters\n----------\nx : int\n    The x.\n')
    assert lexed.summary is None
    assert len(lexed.sections) == 1


# Header detection ###########################################################


def test_numpy_headers_are_detected():
    lexed = lex('S.\n\nParameters\n----------\nx : int\n\nNotes\n-----\nA.\n')
    assert [s.name for s in lexed.sections] == ['Parameters', 'Notes']
    assert {s.style for s in lexed.sections} == {'numpy'}


def test_google_headers_are_detected():
    lexed = lex('S.\n\nArgs:\n    x (int): The x.\n\nNotes:\n    A note.\n')
    assert [s.name for s in lexed.sections] == ['Args', 'Notes']
    assert {s.style for s in lexed.sections} == {'google'}


def test_unknown_section_titles_are_still_sections():
    lexed = lex('S.\n\nEfferents\n---------\nDownstream.\n')
    assert [s.name for s in lexed.sections] == ['Efferents']


def test_multiword_section_titles():
    lexed = lex('S.\n\nSee Also\n--------\nsomething\n')
    assert lexed.sections[0].name == 'See Also'


def test_a_short_underline_is_not_a_header():
    # Fewer than three dashes is prose, not a section underline.
    lexed = lex('Summary.\n\nEmphasis\n--\nMore text.\n')
    assert lexed.sections == ()


def test_a_trailing_google_title_with_no_body_is_not_a_header():
    # Nothing follows the colon at all, so there is no body to indent.
    lexed = lex('Summary.\n\nNotes:\n')
    assert lexed.sections == ()


def test_a_google_header_may_be_followed_by_a_blank_line():
    lexed = lex('Summary.\n\nArgs:\n\n    x (int): The x.\n')
    assert [s.name for s in lexed.sections] == ['Args']
    assert lexed.sections[0].body == ('x (int): The x.',)


def test_a_google_header_needs_an_indented_body():
    # Without an indented body this is ordinary prose, not a section.
    lexed = lex('Summary.\n\nNote:\nThis is not a section.\n')
    assert lexed.sections == ()


def test_an_indented_line_is_never_a_header():
    text = 'Summary.\n\nNotes\n-----\n    Args:\n        Not a section.\n'
    lexed = lex(text)
    assert [s.name for s in lexed.sections] == ['Notes']


def test_example_bodies_do_not_produce_spurious_headers():
    text = 'Summary.\n\nExamples\n--------\n>>> compute(1)\n2\n'
    lexed = lex(text)
    assert [s.name for s in lexed.sections] == ['Examples']
    assert lexed.sections[0].body == ('>>> compute(1)', '2')


def test_section_bodies_are_dedented():
    lexed = lex('S.\n\nArgs:\n    x (int): The x.\n        More.\n')
    assert lexed.sections[0].body == ('x (int): The x.', '    More.')


def test_section_body_blank_edges_are_trimmed():
    lexed = lex('S.\n\nNotes\n-----\n\nA note.\n\n\n')
    assert lexed.sections[0].body == ('A note.',)


def test_a_section_may_be_empty():
    lexed = lex('S.\n\nNotes\n-----\n\nParameters\n----------\nx : int\n')
    assert lexed.sections[0].name == 'Notes'
    assert lexed.sections[0].body == ()


def test_section_order_is_preserved():
    text = (
        'S.\n\n'
        'Returns\n-------\nint\n\n'
        'Parameters\n----------\nx : int\n\n'
        'Notes\n-----\nA.\n'
    )
    assert [s.name for s in lex(text).sections] == [
        'Returns',
        'Parameters',
        'Notes',
    ]


# iter_blocks ################################################################


def test_iter_blocks_splits_on_column_zero():
    body = ('x : int', '    The x.', 'y : int', '    The y.')
    assert list(iter_blocks(body)) == [
        ('x : int', ('The x.',)),
        ('y : int', ('The y.',)),
    ]


def test_iter_blocks_dedents_descriptions():
    body = ('x : int', '    The x.', '        Indented further.')
    assert list(iter_blocks(body)) == [
        ('x : int', ('The x.', '    Indented further.')),
    ]


def test_iter_blocks_handles_items_without_descriptions():
    assert list(iter_blocks(('x : int', 'y : int'))) == [
        ('x : int', ()),
        ('y : int', ()),
    ]


def test_iter_blocks_keeps_internal_blank_lines():
    body = ('x : int', '    One.', '', '    Two.')
    assert list(iter_blocks(body)) == [('x : int', ('One.', '', 'Two.'))]


def test_iter_blocks_of_an_empty_body():
    assert list(iter_blocks(())) == []


def test_iter_blocks_ignores_leading_indented_lines():
    assert list(iter_blocks(('    orphaned',))) == []


# Format detection ###########################################################


def test_detect_numpy():
    assert detect_format(lex('S.\n\nNotes\n-----\nA.\n')) == 'numpy'


def test_detect_google():
    assert detect_format(lex('S.\n\nNotes:\n    A.\n')) == 'google'


def test_detect_returns_none_without_sections():
    # Such a document means the same thing in either format, so there is no
    # arbitrary choice to make and no reason to raise.
    assert detect_format(lex('Just a summary.')) is None
    assert detect_format(lex(None)) is None


def test_detect_rejects_a_mixed_document():
    text = 'S.\n\nParameters\n----------\nx : int\n\nReturns:\n    int\n'
    with pytest.raises(DocFormatError, match='mixes'):
        detect_format(lex(text))


def test_the_mixed_document_error_names_both_sections():
    text = 'S.\n\nParameters\n----------\nx : int\n\nReturns:\n    int\n'
    with pytest.raises(DocFormatError) as info:
        detect_format(lex(text))
    assert "'Parameters'" in str(info.value)
    assert "'Returns'" in str(info.value)
    assert 'format=' in str(info.value)


# Style-restricted lexing ###################################################


def test_restricting_to_numpy_ignores_google_headers():
    lexed = lex('S.\n\nArgs:\n    x (int): The x.\n', styles=('numpy',))
    assert lexed.sections == ()


def test_restricting_to_google_ignores_numpy_headers():
    lexed = lex('S.\n\nNotes\n-----\nA.\n', styles=('google',))
    assert lexed.sections == ()


def test_an_empty_numpy_type_is_not_a_google_header():
    # `x :` has the shape of a Google header, but inside a NumPy section
    # body it is an item declaration with no type.
    text = 'S.\n\nParameters\n----------\nx :\n    The x.\n'
    lexed = lex(text)
    assert [s.name for s in lexed.sections] == ['Parameters']
    assert lexed.styles == frozenset({'numpy'})


def test_a_recognized_google_header_after_numpy_is_still_seen():
    # A real section title is a genuine format conflict and must surface.
    text = 'S.\n\nParameters\n----------\nx : int\n\nReturns:\n    int\n'
    lexed = lex(text)
    assert lexed.styles == frozenset({'numpy', 'google'})


def test_an_unrecognized_google_header_before_numpy_is_seen():
    text = 'S.\n\nEfferents:\n    Downstream.\n\nNotes\n-----\nA.\n'
    lexed = lex(text)
    assert [s.name for s in lexed.sections] == ['Efferents', 'Notes']


# A parameter that looks like a Google header ################################


@pytest.mark.parametrize(
    'declaration',
    ['method : str', 'method : str, optional', 'method', 'method : int'],
)
def test_a_typed_parameter_named_after_a_section_is_unambiguous(declaration):
    text = f'S.\n\nParameters\n----------\n{declaration}\n    The one.\n'
    assert detect_format(lex(text)) == 'numpy'


@pytest.mark.parametrize('declaration', ['method :', 'method:'])
def test_an_untyped_parameter_named_after_a_section_is_ambiguous(declaration):
    text = f'S.\n\nParameters\n----------\n{declaration}\n    The one.\n'
    with pytest.raises(DocFormatError, match='mixes'):
        detect_format(lex(text))


def test_the_ambiguity_error_explains_the_empty_type():
    text = 'S.\n\nParameters\n----------\nmethod :\n    The method.\n'
    with pytest.raises(DocFormatError) as info:
        detect_format(lex(text))
    message = str(info.value)
    assert 'empty type' in message
    assert 'drop the colon' in message
    assert 'format=' in message


def test_a_genuinely_mixed_document_gets_no_declaration_hint():
    # Here the Google section comes first, so it is not inside a NumPy one.
    text = 'S.\n\nArgs:\n    x (int): X.\n\nReturns\n-------\nint\n'
    with pytest.raises(DocFormatError) as info:
        detect_format(lex(text))
    assert 'empty type' not in str(info.value)


def test_a_document_with_no_numpy_sections_gets_no_declaration_hint():
    from docshare._lex import _declaration_hint

    assert _declaration_hint(lex('S.\n\nArgs:\n    x (int): X.\n')) == ''


def test_an_explicit_format_resolves_the_ambiguity():
    text = 'S.\n\nParameters\n----------\nmethod :\n    The method.\n'
    lexed = lex(text, styles=('numpy',))
    assert [s.name for s in lexed.sections] == ['Parameters']


# A dashes rule inside prose (docs/deferred.md item 3) #######################

def test_an_underlined_title_inside_prose_opens_a_section():
    text = (
        'S.\n\nNotes\n-----\nProse.\n\nBackground\n----------\nMore.\n'
    )
    assert [s.name for s in lex(text).sections] == ['Notes', 'Background']


def test_the_split_section_is_opaque_so_nothing_is_lost():
    from docshare import docparse
    from docshare._render import render_document

    text = (
        'S.\n\nNotes\n-----\nProse.\n\nBackground\n----------\nMore.\n'
    )
    doc = docparse(text)
    assert doc.section('Background').opaque
    assert render_document(doc) == text.rstrip()


def test_another_underline_character_is_not_a_header():
    # reStructuredText allows any of several underline characters; only
    # dashes open a section, so a subsection can avoid the split.
    text = 'S.\n\nNotes\n-----\nProse.\n\nBackground\n~~~~~~~~~~\nMore.\n'
    assert [s.name for s in lex(text).sections] == ['Notes']
