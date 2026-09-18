# -*- coding: utf-8 -*-
"""Tests for the recognized-section registry."""

import pytest

from docshare import DocFormatError, SectionKind, section_kind
from docshare._sections import (
    IDENTITY_NAME,
    IDENTITY_NAME_OR_INDEX,
    IDENTITY_TYPE_OR_INDEX,
    SUPPORTED_FORMATS,
    custom_kind,
    iter_section_kinds,
    kind_name,
    normalize_title,
    render_kind,
    section_title,
)
from docshare._signature import PARAMETER_KINDS

ALL_KINDS = tuple(iter_section_kinds())

STRUCTURED = {
    'parameters',
    'other_parameters',
    'keyword_arguments',
    'returns',
    'yields',
    'receives',
    'raises',
    'warns',
    'attributes',
    'methods',
}
PROSE = {'warnings', 'see_also', 'notes', 'references', 'examples'}


def test_registry_covers_the_expected_kinds():
    assert {k.name for k in ALL_KINDS} == STRUCTURED | PROSE


@pytest.mark.parametrize(
    ('title', 'expected'),
    [
        ('Parameters', 'parameters'),
        ('parameters', 'parameters'),
        ('PARAMETERS', 'parameters'),
        ('Args', 'parameters'),
        ('Args:', 'parameters'),
        ('Arguments', 'parameters'),
        ('  Args  :  ', 'parameters'),
        ('Other Parameters', 'other_parameters'),
        ('Other   Parameters', 'other_parameters'),
        ('Keyword Args', 'keyword_arguments'),
        ('Keyword Arguments', 'keyword_arguments'),
        ('Returns', 'returns'),
        ('Return', 'returns'),
        ('Yields', 'yields'),
        ('Receives', 'receives'),
        ('Raises', 'raises'),
        ('Exceptions', 'raises'),
        ('Warns', 'warns'),
        ('Warnings', 'warnings'),
        ('Warning', 'warnings'),
        ('Attributes', 'attributes'),
        ('Methods', 'methods'),
        ('See Also', 'see_also'),
        ('see also', 'see_also'),
        ('Notes', 'notes'),
        ('Note', 'notes'),
        ('References', 'references'),
        ('Examples', 'examples'),
        ('Example', 'examples'),
    ],
)
def test_titles_resolve_to_their_kind(title, expected):
    kind = section_kind(title)
    assert kind is not None
    assert kind.name == expected


def test_normalized_kind_names_resolve():
    # 'see_also' is the kind name; 'see also' is the title.
    assert section_kind('see_also').name == 'see_also'
    assert section_kind('other_parameters').name == 'other_parameters'


@pytest.mark.parametrize(
    'title',
    ['Efferents', 'Afferents', 'Todo', '', 'Random Section', 'Warnings Too'],
)
def test_unrecognized_titles_are_opaque(title):
    assert section_kind(title) is None


def test_warns_and_warnings_are_distinct():
    assert section_kind('Warns').name == 'warns'
    assert section_kind('Warnings').name == 'warnings'
    assert section_kind('Warns') is not section_kind('Warnings')


@pytest.mark.parametrize('kind', ALL_KINDS, ids=lambda k: k.name)
def test_structured_flag_matches_expectation(kind):
    assert kind.structured == (kind.name in STRUCTURED)


@pytest.mark.parametrize('kind', ALL_KINDS, ids=lambda k: k.name)
def test_identity_is_set_only_for_structured_kinds(kind):
    if kind.structured:
        assert kind.identity in (
            IDENTITY_NAME,
            IDENTITY_NAME_OR_INDEX,
            IDENTITY_TYPE_OR_INDEX,
        )
    else:
        assert kind.identity is None


@pytest.mark.parametrize(
    ('name', 'identity'),
    [
        ('parameters', IDENTITY_NAME),
        ('attributes', IDENTITY_NAME),
        ('returns', IDENTITY_NAME_OR_INDEX),
        ('yields', IDENTITY_NAME_OR_INDEX),
        ('raises', IDENTITY_TYPE_OR_INDEX),
        ('warns', IDENTITY_TYPE_OR_INDEX),
    ],
)
def test_identity_schemes(name, identity):
    assert section_kind(name).identity == identity


@pytest.mark.parametrize('kind', ALL_KINDS, ids=lambda k: k.name)
def test_every_kind_has_a_title_in_every_format(kind):
    for fmt in SUPPORTED_FORMATS:
        title = section_title(kind, fmt)
        assert isinstance(title, str) and title


@pytest.mark.parametrize('kind', ALL_KINDS, ids=lambda k: k.name)
def test_canonical_titles_round_trip_to_their_own_kind(kind):
    for fmt in SUPPORTED_FORMATS:
        assert section_kind(section_title(kind, fmt)) is kind


def test_parameters_differs_between_formats():
    assert section_title('parameters', 'numpy') == 'Parameters'
    assert section_title('parameters', 'google') == 'Args'


def test_section_title_accepts_a_kind_or_a_name_or_a_title():
    kind = section_kind('parameters')
    assert section_title(kind, 'numpy') == 'Parameters'
    assert section_title('parameters', 'numpy') == 'Parameters'
    assert section_title('Args', 'numpy') == 'Parameters'


def test_section_title_rejects_an_unsupported_format():
    with pytest.raises(DocFormatError, match='unsupported documentation'):
        section_title('parameters', 'rest')


def test_section_title_rejects_an_unrecognized_kind():
    with pytest.raises(DocFormatError, match='unrecognized documentation'):
        section_title('Efferents', 'numpy')


def test_aliases_are_unique_across_kinds():
    seen = {}
    for kind in ALL_KINDS:
        for alias in kind.aliases:
            assert alias not in seen, f'{alias} claimed twice'
            seen[alias] = kind.name


def test_aliases_are_already_normalized():
    for kind in ALL_KINDS:
        for alias in kind.aliases:
            assert normalize_title(alias) == alias


def test_kinds_are_immutable():
    kind = section_kind('parameters')
    assert isinstance(kind, SectionKind)
    with pytest.raises(Exception):  # noqa: B017 - FrozenInstanceError
        kind.name = 'nope'


def test_kind_titles_mapping_is_read_only():
    kind = section_kind('parameters')
    with pytest.raises(TypeError):
        kind.titles['numpy'] = 'Nope'


def test_keyword_arguments_merge_into_parameters_in_numpy():
    # The NumPy standard has no keyword-argument section; numpydoc documents
    # keyword arguments in Parameters.
    assert render_kind('keyword_arguments', 'numpy').name == 'parameters'


def test_keyword_arguments_stay_distinct_in_google():
    assert render_kind('keyword_arguments', 'google').name == (
        'keyword_arguments'
    )


@pytest.mark.parametrize('kind', ALL_KINDS, ids=lambda k: k.name)
def test_only_keyword_arguments_is_merged(kind):
    if kind.name == 'keyword_arguments':
        assert dict(kind.merges) == {'numpy': 'parameters'}
    else:
        assert dict(kind.merges) == {}


@pytest.mark.parametrize('kind', ALL_KINDS, ids=lambda k: k.name)
def test_unmerged_kinds_render_as_themselves(kind):
    for fmt in SUPPORTED_FORMATS:
        if fmt not in kind.merges:
            assert render_kind(kind, fmt) is kind


@pytest.mark.parametrize('kind', ALL_KINDS, ids=lambda k: k.name)
def test_a_merge_target_is_never_itself_merged(kind):
    # Guards against a merge chain, which the renderer does not follow.
    for fmt, target in kind.merges.items():
        assert fmt not in section_kind(target).merges


@pytest.mark.parametrize('kind', ALL_KINDS, ids=lambda k: k.name)
def test_a_merge_preserves_structuredness(kind):
    for target in kind.merges.values():
        assert section_kind(target).structured == kind.structured
        assert section_kind(target).identity == kind.identity


def test_render_kind_accepts_a_kind_or_a_title():
    kind = section_kind('parameters')
    assert render_kind(kind, 'numpy') is kind
    assert render_kind('Keyword Args', 'numpy').name == 'parameters'


def test_render_kind_rejects_an_unsupported_format():
    with pytest.raises(DocFormatError, match='unsupported documentation'):
        render_kind('parameters', 'rest')


def test_render_kind_rejects_an_unrecognized_kind():
    with pytest.raises(DocFormatError, match='unrecognized documentation'):
        render_kind('Efferents', 'numpy')


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('Parameters', 'parameters'),
        ('Args:', 'args'),
        ('  See   Also  ', 'see also'),
        ('Returns :', 'returns'),
        ('', ''),
    ],
)
def test_normalize_title(raw, expected):
    assert normalize_title(raw) == expected


# Declared sections ##########################################################


def test_a_declared_kind_borrows_how_its_body_is_read():
    kind = custom_kind('Inputs', 'Parameters')
    model = section_kind('parameters')
    assert kind.name == 'inputs'
    assert kind.structured is model.structured
    assert kind.identity is model.identity
    assert kind.placeholder == model.placeholder


def test_a_declared_kind_keeps_its_own_spelling_in_both_formats():
    kind = custom_kind('Inputs', 'Parameters')
    assert dict(kind.titles) == {'numpy': 'Inputs', 'google': 'Inputs'}


def test_a_declared_kind_is_never_merged():
    # It has no equivalent in either format to be folded into.
    kind = custom_kind('Keyword Inputs', 'Keyword Args')
    assert dict(kind.merges) == {}
    for format in SUPPORTED_FORMATS:
        assert render_kind(kind, format) is kind


def test_a_declared_kind_is_hashable():
    # A Section carries its declared kind, and every record in the model is
    # hashable as a whole.
    assert hash(custom_kind('Inputs', 'Parameters')) is not None


def test_a_declared_kind_is_not_a_parameter_kind():
    # It documents something other than the callable's parameters, so it is
    # never checked against a signature.
    assert custom_kind('Inputs', 'Parameters').name not in PARAMETER_KINDS


def test_a_declared_kind_borrows_a_placeholder():
    assert custom_kind('Products', 'Returns').placeholder == 'object'


def test_a_declared_kind_may_resemble_a_prose_section():
    kind = custom_kind('Caveats', 'Notes')
    assert kind.structured is False
    assert kind.identity is None


def test_a_recognized_title_cannot_be_declared():
    with pytest.raises(DocFormatError, match='already recognizes'):
        custom_kind('Parameters', 'Returns')


def test_a_recognized_title_cannot_be_declared_by_an_alias():
    with pytest.raises(DocFormatError, match='already recognizes'):
        custom_kind('Args', 'Returns')


@pytest.mark.parametrize('title', ['Model I/O', 'In:puts', '2Inputs', ''])
def test_a_title_no_docstring_could_express_is_refused(title):
    with pytest.raises(DocFormatError, match='cannot be a section title'):
        custom_kind(title, 'Parameters')


def test_resembling_something_unrecognized_is_refused():
    with pytest.raises(DocFormatError, match='not a section docshare'):
        custom_kind('Inputs', 'Efferents')


def test_a_declared_title_may_have_several_words():
    assert custom_kind('Model Inputs', 'Parameters').name == 'model_inputs'


def test_kind_name_normalizes_a_title():
    assert kind_name('See Also') == 'see_also'
    assert kind_name('Inputs:') == 'inputs'
