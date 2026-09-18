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


def test_an_unrecognized_google_header_is_not_a_section():
    # Google style defines a fixed set of section names, and a colon is
    # ordinary punctuation, so an unrecognized title is prose.
    text = 'S.\n\nEfferents:\n    Downstream.\n\nNotes\n-----\nA.\n'
    lexed = lex(text)
    assert [s.name for s in lexed.sections] == ['Notes']
    assert lexed.description == ('Efferents:', '    Downstream.')


# A sentence that ends in a colon ############################################


PROSE = """Do a thing.

The tuple has the following elements:

    a : the first
    b : the second

Parameters
----------
x : int
    The x.
"""


def test_a_sentence_ending_in_a_colon_is_not_a_section():
    lexed = lex(PROSE)
    assert [s.name for s in lexed.sections] == ['Parameters']
    assert 'The tuple has the following elements:' in lexed.description


def test_a_sentence_ending_in_a_colon_does_not_make_a_document_ambiguous():
    assert detect_format(lex(PROSE)) == 'numpy'


def test_prose_ending_in_a_colon_leaves_a_document_formatless():
    # With nothing but the prose block, there is no section either way, so
    # the document belongs to neither format rather than to Google.
    lexed = lex('Do a thing.\n\nFor example:\n\n    f(1)\n')
    assert lexed.sections == ()
    assert detect_format(lexed) is None


@pytest.mark.parametrize(
    'lead',
    [
        'For example',
        'Consider the following',
        'The tuple has the following elements',
        'Usage',
    ],
)
def test_common_prose_lead_ins_are_not_sections(lead):
    lexed = lex(f'S.\n\n{lead}:\n\n    indented\n')
    assert lexed.sections == ()


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
    text = 'S.\n\nNotes\n-----\nProse.\n\nBackground\n----------\nMore.\n'
    assert [s.name for s in lex(text).sections] == ['Notes', 'Background']


def test_the_split_section_is_opaque_so_nothing_is_lost():
    from docshare import docparse
    from docshare._render import render_document

    text = 'S.\n\nNotes\n-----\nProse.\n\nBackground\n----------\nMore.\n'
    doc = docparse(text)
    assert doc.section('Background').opaque
    assert render_document(doc) == text.rstrip()


def test_another_underline_character_is_not_a_header():
    # reStructuredText allows any of several underline characters; only
    # dashes open a section, so a subsection can avoid the split.
    text = 'S.\n\nNotes\n-----\nProse.\n\nBackground\n~~~~~~~~~~\nMore.\n'
    assert [s.name for s in lex(text).sections] == ['Notes']


# Google sections end where the indentation does ############################

GOOGLE_WITH_TAIL = (
    'Summary.\n'
    '\n'
    'Attributes:\n'
    '    name: the name.\n'
    '    value: the value.\n'
    '\n'
    'Trailing prose that belongs to the class, not to the section.\n'
    'It continues over two lines.\n'
)


def test_a_google_section_ends_when_the_indentation_does():
    lexed = lex(GOOGLE_WITH_TAIL)
    assert lexed.sections[0].name == 'Attributes'
    assert lexed.sections[0].body == ('name: the name.', 'value: the value.')


def test_trailing_prose_becomes_a_section_with_no_title():
    lexed = lex(GOOGLE_WITH_TAIL)
    assert len(lexed.sections) == 2
    assert lexed.sections[1].name == ''
    assert lexed.sections[1].body == (
        'Trailing prose that belongs to the class, not to the section.',
        'It continues over two lines.',
    )


def test_prose_between_two_google_sections_is_kept_in_place():
    text = (
        'S.\n\nArgs:\n    x (int): X.\n\n'
        'A paragraph between them.\n\n'
        'Returns:\n    int: The result.\n'
    )
    names = [s.name for s in lex(text).sections]
    assert names == ['Args', '', 'Returns']


def test_a_numpy_section_still_runs_to_the_next_header():
    # NumPy bodies sit at column zero, so the rule does not apply to them.
    text = 'S.\n\nNotes\n-----\nA note.\nStill the note.\n'
    lexed = lex(text)
    assert len(lexed.sections) == 1
    assert lexed.sections[0].body == ('A note.', 'Still the note.')


def test_a_google_section_with_no_trailing_prose_gains_no_extra_section():
    lexed = lex('S.\n\nArgs:\n    x (int): X.\n')
    assert [s.name for s in lexed.sections] == ['Args']


def test_a_blank_line_alone_is_not_trailing_prose():
    lexed = lex('S.\n\nArgs:\n    x (int): X.\n\n\n')
    assert [s.name for s in lexed.sections] == ['Args']


# A leading call signature ###################################################

UFUNC = """log(x, /, out=None, *, where=True, casting='same_kind'[, signature])

Natural logarithm, element-wise.

Parameters
----------
x : array_like
    Input value.
"""


def test_a_leading_call_signature_is_not_the_summary():
    lexed = lex(UFUNC)
    assert lexed.signature.startswith('log(x, /, out=None')
    assert lexed.summary == 'Natural logarithm, element-wise.'


def test_a_signature_wrapped_over_several_lines_is_joined():
    text = """spam(a, b,\n     c)\n\nThe summary.\n"""
    lexed = lex(text)
    assert lexed.signature == 'spam(a, b, c)'
    assert lexed.summary == 'The summary.'


def test_a_returned_name_before_the_call_is_part_of_the_signature():
    lexed = lex('y = spam(a, b)\n\nThe summary.\n')
    assert lexed.signature == 'y = spam(a, b)'
    assert lexed.summary == 'The summary.'


def test_an_ordinary_summary_is_not_a_signature():
    lexed = lex('Compute f(x) for each x.\n\nMore.\n')
    assert lexed.signature is None
    assert lexed.summary == 'Compute f(x) for each x.'


def test_a_document_that_is_only_a_signature_keeps_it_as_the_summary():
    # Taking it away would leave the document with nothing at all.
    lexed = lex('spam(a, b)')
    assert lexed.signature is None
    assert lexed.summary == 'spam(a, b)'


def test_a_signature_followed_by_a_section_alone_is_still_a_signature():
    lexed = lex('spam(a, b)\n\nNotes\n-----\nA note.\n')
    assert lexed.signature == 'spam(a, b)'
    assert lexed.summary is None


def test_a_document_with_no_preamble_has_no_signature():
    lexed = lex('Notes\n-----\nA note.\n')
    assert lexed.signature is None
