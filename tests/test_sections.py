# -*- coding: utf-8 -*-
"""Tests for the recognized-section registry."""

import pytest

from docshare import DocFormatError, SectionKind, section_kind
from docshare._sections import (
    IDENTITY_NAME,
    IDENTITY_NAME_OR_INDEX,
    IDENTITY_TYPE_OR_INDEX,
    SUPPORTED_FORMATS,
    iter_section_kinds,
    normalize_title,
    section_title,
)

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
