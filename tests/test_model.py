# -*- coding: utf-8 -*-
"""Tests for the immutable semantic document model."""

import dataclasses

import pytest

from docshare import (
    DocFormatError,
    Document,
    FrozenDict,
    Item,
    Section,
    section_kind,
)
from docshare._sections import custom_kind

# FrozenDict ##################################################################


def test_frozendict_behaves_like_a_mapping():
    d = FrozenDict({'a': 1, 'b': 2})
    assert d['a'] == 1
    assert len(d) == 2
    assert set(d) == {'a', 'b'}
    assert dict(d) == {'a': 1, 'b': 2}


def test_frozendict_accepts_kwargs_and_pairs():
    assert dict(FrozenDict(a=1)) == {'a': 1}
    assert dict(FrozenDict([('a', 1)])) == {'a': 1}
    assert dict(FrozenDict({'a': 1}, b=2)) == {'a': 1, 'b': 2}


def test_frozendict_cannot_be_mutated():
    d = FrozenDict({'a': 1})
    with pytest.raises(TypeError):
        d['b'] = 2
    with pytest.raises(AttributeError):
        d.a = 2


def test_frozendict_equality_with_plain_dicts():
    assert FrozenDict({'a': 1}) == {'a': 1}
    assert FrozenDict({'a': 1}) == FrozenDict({'a': 1})
    assert FrozenDict({'a': 1}) != {'a': 2}
    assert FrozenDict({'a': 1}) != 'not a mapping'


def test_frozendict_is_hashable_and_stable():
    d = FrozenDict({'a': 1, 'b': 2})
    assert hash(d) == hash(FrozenDict({'b': 2, 'a': 1}))
    assert hash(d) == hash(d)  # exercises the cached hash
    assert len({d, FrozenDict({'a': 1, 'b': 2})}) == 1


def test_frozendict_does_not_alias_its_source():
    source = {'a': 1}
    d = FrozenDict(source)
    source['b'] = 2
    assert dict(d) == {'a': 1}


def test_frozendict_repr():
    assert repr(FrozenDict({'a': 1})) == "FrozenDict({'a': 1})"


# Item ########################################################################


def test_item_defaults_are_empty():
    item = Item()
    assert item.names == ()
    assert item.type is None
    assert item.description == ()
    assert dict(item.meta) == {}


def test_item_coerces_a_single_name_to_a_tuple():
    assert Item(names='x').names == ('x',)


def test_item_coerces_name_iterables():
    assert Item(names=['x', 'y']).names == ('x', 'y')


def test_item_coerces_a_description_string_to_lines():
    item = Item(description='First line.\nSecond line.')
    assert item.description == ('First line.', 'Second line.')


def test_item_coerces_meta_to_a_frozendict():
    item = Item(meta={'optional': 'yes'})
    assert isinstance(item.meta, FrozenDict)
    assert item.meta['optional'] == 'yes'


def test_item_accepts_explicit_nones_for_its_sequences():
    item = Item(names=None, description=None, meta=None)
    assert item.names == ()
    assert item.description == ()
    assert dict(item.meta) == {}


def test_section_and_document_accept_explicit_none_text():
    assert Section(name='Efferents', text=None).text == ()
    assert Document(description=None).description == ()


def test_item_is_frozen():
    item = Item(names='x')
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.names = ('y',)


def test_item_is_hashable():
    item = Item(names='x', type='float', description='The x.')
    assert (
        len({item, Item(names='x', type='float', description='The x.')}) == 1
    )


def test_item_equality_ignores_construction_style():
    assert Item(names='x', description='One.') == Item(
        names=('x',), description=('One.',)
    )


def test_item_group_detection():
    assert not Item(names='x').grouped
    assert Item(names=('x', 'y')).grouped
    assert not Item().grouped


def test_item_single_name_property():
    assert Item(names='x').name == 'x'
    assert Item(names=('x', 'y')).name is None
    assert Item().name is None


def test_item_evolve_returns_a_new_item():
    item = Item(names='x', type='float')
    other = item.evolve(type='int')
    assert item.type == 'float'
    assert other.type == 'int'
    assert other.names == ('x',)


# Section #####################################################################


def test_section_kind_is_normalized_from_any_alias():
    assert Section(name='Args', kind='Args').kind == 'parameters'
    assert Section(name='Parameters', kind='Parameters').kind == 'parameters'
    assert Section(name='Args', kind='parameters').kind == 'parameters'


def test_section_without_a_kind_is_opaque():
    section = Section(name='Efferents', text='Downstream connections.')
    assert section.opaque
    assert not section.structured
    assert section.kind is None
    assert section.text == ('Downstream connections.',)


def test_recognized_structured_section_is_not_opaque():
    section = Section(name='Parameters', kind='parameters')
    assert not section.opaque
    assert section.structured


def test_recognized_prose_section_is_not_structured():
    section = Section(name='Notes', kind='notes', text='Some prose.')
    assert not section.opaque
    assert not section.structured


def test_section_rejects_an_unrecognized_kind():
    with pytest.raises(DocFormatError, match='unrecognized'):
        Section(name='Efferents', kind='efferents')


def test_prose_section_rejects_items():
    with pytest.raises(DocFormatError, match='prose'):
        Section(name='Notes', kind='notes', items=[Item(names='x')])


def test_opaque_section_rejects_items():
    with pytest.raises(DocFormatError, match='opaque'):
        Section(name='Efferents', items=[Item(names='x')])


def test_section_rejects_non_items():
    with pytest.raises(TypeError, match='Item instances'):
        Section(name='Parameters', kind='parameters', items=['x'])


def test_section_is_frozen():
    section = Section(name='Parameters', kind='parameters')
    with pytest.raises(dataclasses.FrozenInstanceError):
        section.name = 'Args'


def test_section_preserves_item_order():
    items = [Item(names=n) for n in ('c', 'a', 'b')]
    section = Section(name='Parameters', kind='parameters', items=items)
    assert [i.name for i in section.items] == ['c', 'a', 'b']


def test_section_evolve():
    section = Section(name='Parameters', kind='parameters')
    other = section.evolve(name='Args')
    assert section.name == 'Parameters'
    assert other.name == 'Args'
    assert other.kind == 'parameters'


# Document ####################################################################


@pytest.fixture
def document():
    params = Section(
        name='Parameters',
        kind='parameters',
        items=[
            Item(names='x', type='float', description='The x.'),
            Item(names=('y', 'z'), type='float', description='The others.'),
        ],
    )
    returns = Section(
        name='Returns',
        kind='returns',
        items=[Item(type='float', description='The result.')],
    )
    efferents = Section(name='Efferents', text='Downstream connections.')
    return Document(
        summary='Do a thing.',
        description='A longer explanation.',
        sections=[params, returns, efferents],
        format='numpy',
    )


def test_empty_document_is_falsy():
    assert Document().empty
    assert not Document()


def test_nonempty_document_is_truthy(document):
    assert not document.empty
    assert document


def test_a_summary_alone_makes_a_document_nonempty():
    assert Document(summary='Hi.')


def test_a_section_alone_makes_a_document_nonempty():
    assert Document(sections=[Section(name='Notes', kind='notes')])


def test_document_preserves_section_order(document):
    assert [s.name for s in document.sections] == [
        'Parameters',
        'Returns',
        'Efferents',
    ]


def test_document_lookup_by_kind(document):
    assert document.section('parameters').name == 'Parameters'
    assert document.section('returns').name == 'Returns'


def test_document_lookup_accepts_either_format_spelling(document):
    assert document.section('Args') is document.section('Parameters')
    assert document.section('args') is document.section('parameters')


def test_document_lookup_of_an_opaque_section_by_name(document):
    section = document.section('Efferents')
    assert section is not None
    assert section.opaque


def test_document_lookup_of_an_opaque_section_ignores_case(document):
    assert document.section('efferents') is document.section('Efferents')


def test_document_lookup_returns_none_when_absent(document):
    assert document.section('raises') is None
    assert document.section('Afferents') is None


def test_document_iter_sections_finds_every_match():
    a = Section(name='Notes', kind='notes', text='One.')
    b = Section(name='Notes', kind='notes', text='Two.')
    doc = Document(sections=[a, b])
    assert list(doc.iter_sections('notes')) == [a, b]
    assert doc.section('notes') is a


def test_document_rejects_an_unsupported_format():
    with pytest.raises(DocFormatError, match='unsupported'):
        Document(format='rest')


def test_document_allows_a_null_format():
    assert Document(format=None).format is None


def test_document_rejects_non_sections():
    with pytest.raises(TypeError, match='Section instances'):
        Document(sections=['Parameters'])


def test_document_is_frozen(document):
    with pytest.raises(dataclasses.FrozenInstanceError):
        document.summary = 'Nope.'


def test_document_evolve(document):
    other = document.evolve(summary='Something else.')
    assert document.summary == 'Do a thing.'
    assert other.summary == 'Something else.'
    assert other.sections == document.sections


def test_document_description_is_split_into_lines():
    doc = Document(description='One.\nTwo.')
    assert doc.description == ('One.', 'Two.')


def test_grouped_item_survives_the_model(document):
    params = document.section('parameters')
    grouped = params.items[1]
    assert grouped.grouped
    assert grouped.names == ('y', 'z')


# Declared sections ##########################################################

INPUTS = custom_kind('Inputs', 'Parameters')
CAVEATS = custom_kind('Caveats', 'Notes')


def test_a_declared_section_takes_its_kind_from_its_declaration():
    section = Section(name='Inputs', custom=INPUTS)
    assert section.kind == 'inputs'
    assert section.spec is INPUTS
    assert not section.opaque


def test_a_declared_section_is_structured_like_what_it_resembles():
    assert Section(name='Inputs', custom=INPUTS).structured is True
    assert Section(name='Caveats', custom=CAVEATS).structured is False


def test_a_declared_prose_section_cannot_hold_items():
    with pytest.raises(DocFormatError, match='is prose'):
        Section(
            name='Caveats',
            custom=CAVEATS,
            items=(Item(names=('x',)),),
        )


def test_a_declared_section_may_state_its_own_kind():
    section = Section(name='Inputs', kind='inputs', custom=INPUTS)
    assert section.kind == 'inputs'


def test_a_declared_section_whose_kind_disagrees_is_refused():
    with pytest.raises(DocFormatError, match='carries the custom kind'):
        Section(name='Inputs', kind='parameters', custom=INPUTS)


def test_a_custom_kind_must_be_a_section_kind():
    with pytest.raises(TypeError, match='must be a SectionKind'):
        Section(name='Inputs', custom='inputs')


def test_a_custom_kind_cannot_shadow_a_registered_one():
    shadow = dataclasses.replace(INPUTS, name='parameters')
    with pytest.raises(DocFormatError, match='already recognizes'):
        Section(name='Inputs', custom=shadow)


def test_an_unregistered_kind_without_a_declaration_is_refused():
    with pytest.raises(DocFormatError, match='unrecognized documentation'):
        Section(name='Inputs', kind='inputs')


def test_a_declared_section_survives_evolving():
    section = Section(name='Inputs', custom=INPUTS)
    assert section.evolve(items=(Item(names=('x',)),)).spec is INPUTS


def test_an_opaque_section_has_no_spec():
    assert Section(name='Efferents').spec is None


def test_a_registered_section_reports_its_registered_spec():
    assert Section(name='Notes', kind='notes').spec is section_kind('notes')


# Looking a declared section up ##############################################


DECLARED = Document(
    summary='S.',
    sections=(
        Section(
            name='Parameters',
            kind='parameters',
            items=(Item(names=('w',), description=('The weights.',)),),
        ),
        Section(
            name='Inputs',
            custom=INPUTS,
            items=(Item(names=('x',), description=('The data.',)),),
        ),
    ),
    format='numpy',
)


@pytest.mark.parametrize('key', ['Inputs', 'inputs', 'INPUTS', 'Inputs:'])
def test_a_declared_section_answers_to_its_own_title(key):
    assert DECLARED.section(key).name == 'Inputs'


def test_a_declared_section_does_not_answer_to_what_it_resembles():
    # The two coexist and mean different things; that is the whole point.
    assert DECLARED.section('Parameters').name == 'Parameters'


def test_a_document_of_declared_sections_is_still_hashable():
    assert hash(DECLARED) is not None


def test_another_unregistered_title_does_not_match_a_declared_section():
    assert DECLARED.section('Efferents') is None
