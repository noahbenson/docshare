# -*- coding: utf-8 -*-
"""Tests for the inheritance engine.

The worked examples of the specification, sections 49 to 56, appear here
verbatim, alongside the invariants of section 61.
"""

import pytest

from docshare import (
    DocInheritanceError,
    DocMappingError,
    Document,
    Item,
    Section,
    clear_docinfo,
    docparse,
)
from docshare._inherit import (
    DESCRIPTION,
    SUMMARY,
    Operation,
    _resolve_sources,
    compose,
)
from docshare._sections import section_kind


@pytest.fixture(autouse=True)
def _empty_cache():
    clear_docinfo()
    yield
    clear_docinfo()


def run(obj, *operations, extraparam=None):
    """Compose `obj` against `operations` and return the document."""
    return compose(obj, docparse(obj), operations, extraparam=extraparam)


def params(doc):
    """Return ``(names, description)`` for each documented parameter."""
    section = doc.section('parameters')
    if section is None:
        return []
    return [(item.names, item.description) for item in section.items]


def names(doc, kind='parameters'):
    """Return the flattened item names of a section."""
    section = doc.section(kind)
    return [] if section is None else [i.names for i in section.items]


def descriptions(doc, kind='parameters'):
    """Return the first description line of each item of a section."""
    section = doc.section(kind)
    if section is None:
        return []
    return [i.description[0] if i.description else None for i in section.items]


# Sources ####################################################################


def quuxatize(foo, bar=1):
    """Compute a quux.

    Parameters
    ----------
    foo : float
        The foo parameter.
    bar : float, optional
        The bar parameter; the default is 1.

    Returns
    -------
    float
        The quux.
    """


def alpha(x, y):
    """Alpha.

    Parameters
    ----------
    x : int
        x from alpha.
    y : int
        y from alpha.
    """


def beta(x, y):
    """Beta.

    Parameters
    ----------
    x : int
        x from beta.
    """


def gamma(x, y):
    """Gamma.

    Parameters
    ----------
    y : int
        y from gamma.
    """


def grouped(x, y, z):
    """Grouped.

    Parameters
    ----------
    x, y : float
        Cartesian coordinates.
    z : int
        Depth.
    """


def four_returns():
    """Four returns.

    Returns
    -------
    float
        First.
    float
        Second.
    float
        Third.
    float
        Fourth.

    Raises
    ------
    ValueError
        If bad.
    TypeError
        If wrong.

    Yields
    ------
    int
        Each value.

    Attributes
    ----------
    value : int
        The value.

    Notes
    -----
    A note from the source.

    Examples
    --------
    >>> four_returns()

    Efferents
    ---------
    Downstream connections.
    """


# Section 49 and 60: the guiding example #####################################


def test_the_guiding_example():
    def logquuxatize(foo, bar=1, base=None):
        """Compute the logarithm of a quux.

        Parameters
        ----------
        base : float, optional
            The logarithm base; the default is ``None``.

        Returns
        -------
        float
            The logarithm of the quux.
        """

    doc = run(logquuxatize, Operation('parameters', sources=(quuxatize,)))
    assert names(doc) == [('foo',), ('bar',), ('base',)]
    assert descriptions(doc) == [
        'The foo parameter.',
        'The bar parameter; the default is 1.',
        'The logarithm base; the default is ``None``.',
    ]


def test_the_summary_is_never_replaced():
    def target(foo, bar=1):
        """My own summary."""

    doc = run(target, Operation('parameters', sources=(quuxatize,)))
    assert doc.summary == 'My own summary.'


def test_the_description_is_never_replaced():
    def source(x):
        """S.

        Source description.

        Parameters
        ----------
        x : int
            The x.
        """

    def target(x):
        """T."""

    doc = run(target, Operation('parameters', sources=(source,)))
    assert doc.description == ()


# Section 61.1: explicit documentation wins ##################################


def test_target_documentation_overrides_inherited():
    def target(x, y):
        """T.

        Parameters
        ----------
        x : int
            My own x.
        """

    doc = run(target, Operation('parameters', sources=(alpha,)))
    assert descriptions(doc) == ['My own x.', 'y from alpha.']


# Section 52 and 61.2: right-most precedence #################################


def test_the_rightmost_source_wins():
    def target(x, y):
        """T."""

    doc = run(target, Operation('parameters', sources=(alpha, beta)))
    assert descriptions(doc) == ['x from beta.', 'y from alpha.']


def test_precedence_across_three_sources():
    def target(x, y):
        """T."""

    doc = run(target, Operation('parameters', sources=(alpha, beta, gamma)))
    assert descriptions(doc) == ['x from beta.', 'y from gamma.']


def test_a_single_source_need_not_be_a_sequence():
    def target(x, y):
        """T."""

    doc = run(target, Operation('parameters', sources=(alpha,)))
    assert descriptions(doc) == ['x from alpha.', 'y from alpha.']


# Section 53 and 61.3: forced source selection ###############################


def test_a_bound_source_overrides_precedence():
    def target(x, y):
        """T."""

    doc = run(
        target,
        Operation('parameters', sources=(alpha, beta, gamma, (alpha, 'x'))),
    )
    assert descriptions(doc) == ['x from alpha.', 'y from gamma.']


def test_a_bound_source_leaves_other_items_alone():
    def target(x, y):
        """T."""

    doc = run(
        target, Operation('parameters', sources=(alpha, gamma, (alpha, 'y')))
    )
    assert descriptions(doc) == ['x from alpha.', 'y from alpha.']


def test_a_pair_ending_in_a_string_is_an_item_binding():
    specs = _resolve_sources(((alpha, 'x'),))
    assert specs[0].obj is alpha
    assert specs[0].key == 'x'


def test_a_pair_ending_in_an_integer_is_an_item_binding():
    specs = _resolve_sources(((four_returns, 2),))
    assert specs[0].obj is four_returns
    assert specs[0].key == 2


def test_two_sources_are_not_mistaken_for_a_binding():
    # A source is an object with documentation, never a string or an
    # integer, so a pair of sources is unambiguous.
    specs = _resolve_sources((alpha, beta))
    assert [spec.key for spec in specs] == [None, None]
    assert [spec.obj for spec in specs] == [alpha, beta]


def test_a_boolean_is_not_an_item_key():
    # bool is a subclass of int, but True is not a position.
    specs = _resolve_sources(((alpha, True),))
    assert specs[0].key is None


# Section 50 and 61.4: dropping ##############################################


def test_dropping_excludes_a_parameter_from_inheritance():
    def target(x, y):
        """T."""

    doc = run(
        target,
        Operation('parameters', sources=(alpha,), drop=frozenset({'x'})),
    )
    assert names(doc) == [('y',)]


def test_dropping_does_not_remove_the_targets_own_documentation():
    def target(x, y):
        """T.

        Parameters
        ----------
        x : int
            My own x.
        """

    doc = run(
        target,
        Operation('parameters', sources=(alpha,), drop=frozenset({'x'})),
    )
    assert descriptions(doc) == ['My own x.', 'y from alpha.']


# Section 51: parameter mapping ##############################################


def test_a_mapped_parameter_inherits_under_its_own_name():
    def target(inp, scale=1):
        """T."""

    doc = run(
        target,
        Operation('parameters', sources=(alpha,), mapping={'inp': 'x'}),
    )
    assert names(doc) == [('inp',)]
    assert descriptions(doc) == ['x from alpha.']


def test_mapping_does_not_inherit_unrelated_source_parameters():
    def target(inp, scale=1):
        """T."""

    doc = run(
        target,
        Operation('parameters', sources=(alpha,), mapping={'inp': 'x'}),
    )
    assert [n for (n, _) in params(doc)] == [('inp',)]


def test_a_source_parameter_the_target_lacks_is_not_inherited():
    def target(x):
        """T."""

    doc = run(target, Operation('parameters', sources=(alpha,)))
    assert names(doc) == [('x',)]


# Section 21 and 61.5: grouped declarations ##################################


def test_a_group_is_inherited_unchanged():
    def target(x, y, z):
        """T."""

    doc = run(target, Operation('parameters', sources=(grouped,)))
    assert names(doc) == [('x', 'y'), ('z',)]


def test_a_group_completely_replaced_by_the_target():
    def target(x, y, z):
        """T.

        Parameters
        ----------
        x : float
            Horizontal.
        y : float
            Vertical.
        """

    doc = run(target, Operation('parameters', sources=(grouped,)))
    assert names(doc) == [('x',), ('y',), ('z',)]
    assert descriptions(doc) == ['Horizontal.', 'Vertical.', 'Depth.']


def test_partially_overriding_a_group_is_an_error():
    def target(x, y, z):
        """T.

        Parameters
        ----------
        x : float
            Horizontal only.
        """

    with pytest.raises(DocInheritanceError, match='whole or not at all'):
        run(target, Operation('parameters', sources=(grouped,)))


def test_the_partial_group_error_names_the_group_and_the_reason():
    def target(x, y, z):
        """T.

        Parameters
        ----------
        x : float
            Horizontal only.
        """

    with pytest.raises(DocInheritanceError) as info:
        run(target, Operation('parameters', sources=(grouped,)))
    message = str(info.value)
    assert "'x, y'" in message
    assert 'already documented' in message


def test_a_group_member_the_target_lacks_is_an_error():
    def target(x, z):
        """T."""

    with pytest.raises(DocInheritanceError, match='not a parameter'):
        run(target, Operation('parameters', sources=(grouped,)))


def test_dropping_part_of_a_group_is_an_error():
    def target(x, y, z):
        """T."""

    with pytest.raises(DocInheritanceError, match='excluded from inheritance'):
        run(
            target,
            Operation('parameters', sources=(grouped,), drop=frozenset({'y'})),
        )


def test_dropping_a_whole_group_is_allowed():
    def target(x, y, z):
        """T."""

    doc = run(
        target,
        Operation(
            'parameters', sources=(grouped,), drop=frozenset({'x', 'y'})
        ),
    )
    assert names(doc) == [('z',)]


# Section 38: renaming a group ###############################################


def test_renaming_that_keeps_a_group_whole_is_allowed():
    def target(a, y, z):
        """T."""

    doc = run(
        target,
        Operation('parameters', sources=(grouped,), mapping={'a': 'x'}),
    )
    assert names(doc) == [('a', 'y'), ('z',)]
    assert descriptions(doc) == ['Cartesian coordinates.', 'Depth.']


def test_renaming_every_member_of_a_group():
    def target(a, b, z):
        """T."""

    doc = run(
        target,
        Operation(
            'parameters', sources=(grouped,), mapping={'a': 'x', 'b': 'y'}
        ),
    )
    assert names(doc) == [('a', 'b'), ('z',)]


def test_renaming_that_splits_a_group_is_an_error():
    def target(a, z):
        """T."""

    with pytest.raises(DocInheritanceError, match='whole or not at all'):
        run(
            target,
            Operation('parameters', sources=(grouped,), mapping={'a': 'x'}),
        )


def test_the_split_group_error_shows_the_renaming():
    def target(a, z):
        """T."""

    with pytest.raises(DocInheritanceError) as info:
        run(
            target,
            Operation('parameters', sources=(grouped,), mapping={'a': 'x'}),
        )
    assert 'would become a, y' in str(info.value)


# Section 36: empty targets ##################################################


def test_an_undocumented_target_is_composed_from_its_sources():
    def target(foo, bar=1):
        pass

    doc = run(target, Operation('parameters', sources=(quuxatize,)))
    assert names(doc) == [('foo',), ('bar',)]
    assert doc.summary is None


def test_an_undocumented_target_gains_a_section():
    def target(foo, bar=1):
        pass

    doc = run(target, Operation('parameters', sources=(quuxatize,)))
    assert doc.section('parameters') is not None


# Section 37: ordering #######################################################


def test_items_follow_the_signature_order():
    def source(c, a, b):
        """S.

        Parameters
        ----------
        c : int
            The c.
        a : int
            The a.
        b : int
            The b.
        """

    def target(a, b, c):
        """T."""

    doc = run(target, Operation('parameters', sources=(source,)))
    assert names(doc) == [('a',), ('b',), ('c',)]


def test_the_targets_own_items_are_placed_by_signature_too():
    def target(a, b, c):
        """T.

        Parameters
        ----------
        c : int
            My own c.
        """

    def source(a, b, c):
        """S.

        Parameters
        ----------
        a : int
            The a.
        b : int
            The b.
        """

    doc = run(target, Operation('parameters', sources=(source,)))
    assert names(doc) == [('a',), ('b',), ('c',)]
    assert descriptions(doc)[2] == 'My own c.'


def test_extraparam_participates_in_inheritance():
    def source(**kwargs):
        """S.

        Parameters
        ----------
        null : bool
            The null.
        """

    def target(**kwargs):
        """T."""

    doc = run(
        target, Operation('parameters', sources=(source,)), extraparam='null'
    )
    assert names(doc) == [('null',)]


# Sections 23 to 25: returns #################################################


def test_all_source_returns_are_inherited():
    def target():
        """T."""

    doc = run(target, Operation('returns', sources=(four_returns,)))
    assert descriptions(doc, 'returns') == [
        'First.',
        'Second.',
        'Third.',
        'Fourth.',
    ]


def test_dropping_returns_by_position():
    def target():
        """T."""

    doc = run(
        target,
        Operation('returns', sources=(four_returns,), drop=frozenset({0, 2})),
    )
    assert descriptions(doc, 'returns') == ['Second.', 'Fourth.']


def test_dropping_a_single_return():
    def target():
        """T."""

    doc = run(
        target,
        Operation('returns', sources=(four_returns,), drop=frozenset({0})),
    )
    assert descriptions(doc, 'returns') == ['Second.', 'Third.', 'Fourth.']


def test_returnmap_substitutes_the_targets_own_item():
    def target():
        """T.

        Returns
        -------
        float
            Replacement for the third.
        """

    doc = run(
        target, Operation('returns', sources=(four_returns,), mapping={0: 2})
    )
    assert descriptions(doc, 'returns') == [
        'First.',
        'Second.',
        'Replacement for the third.',
        'Fourth.',
    ]


def test_an_unnamed_target_return_without_a_map_is_an_error():
    def target():
        """T.

        Returns
        -------
        float
            Which one is this?
        """

    with pytest.raises(DocInheritanceError, match='unnamed item'):
        run(target, Operation('returns', sources=(four_returns,)))


def test_the_unnamed_return_error_suggests_a_map():
    def target():
        """T.

        Returns
        -------
        float
            Which one is this?
        """

    with pytest.raises(DocInheritanceError) as info:
        run(target, Operation('returns', sources=(four_returns,)))
    assert 'returnmap={0:' in str(info.value)


def test_named_returns_correspond_by_name():
    def source():
        """S.

        Returns
        -------
        total : float
            Source total.
        count : int
            Source count.
        """

    def target():
        """T.

        Returns
        -------
        total : float
            My own total.
        """

    doc = run(target, Operation('returns', sources=(source,)))
    assert descriptions(doc, 'returns') == ['My own total.', 'Source count.']


def test_an_unnamed_target_return_is_fine_when_nothing_is_inherited():
    def target():
        """T.

        Returns
        -------
        float
            The only one.
        """

    doc = run(
        target,
        Operation(
            'returns', sources=(four_returns,), drop=frozenset(range(4))
        ),
    )
    assert descriptions(doc, 'returns') == ['The only one.']


# Raises, yields, attributes #################################################


def test_raises_are_inherited_and_identified_by_type():
    def target():
        """T."""

    doc = run(target, Operation('raises', sources=(four_returns,)))
    assert [i.type for i in doc.section('raises').items] == [
        'ValueError',
        'TypeError',
    ]


def test_raises_can_be_dropped_by_type():
    def target():
        """T."""

    doc = run(
        target,
        Operation(
            'raises', sources=(four_returns,), drop=frozenset({'TypeError'})
        ),
    )
    assert [i.type for i in doc.section('raises').items] == ['ValueError']


def test_yields_are_inherited():
    def target():
        """T."""

    doc = run(target, Operation('yields', sources=(four_returns,)))
    assert descriptions(doc, 'yields') == ['Each value.']


def test_attributes_are_inherited_by_name():
    def target():
        """T."""

    doc = run(target, Operation('attributes', sources=(four_returns,)))
    assert names(doc, 'attributes') == [('value',)]


def test_attributes_have_no_signature_to_order_them():
    def source():
        """S.

        Attributes
        ----------
        b : int
            The b.
        a : int
            The a.
        """

    def target():
        """T."""

    doc = run(target, Operation('attributes', sources=(source,)))
    assert names(doc, 'attributes') == [('b',), ('a',)]


# Prose sections #############################################################


def test_a_prose_section_is_inherited_whole_when_absent():
    def target():
        """T."""

    doc = run(target, Operation('notes', sources=(four_returns,)))
    assert doc.section('notes').text == ('A note from the source.',)


def test_a_prose_section_is_not_replaced_when_present():
    def target():
        """T.

        Notes
        -----
        My own note.
        """

    doc = run(target, Operation('notes', sources=(four_returns,)))
    assert doc.section('notes').text == ('My own note.',)


def test_prose_sections_are_never_merged():
    def target():
        """T.

        Notes
        -----
        My own note.
        """

    doc = run(target, Operation('notes', sources=(four_returns,)))
    assert len(list(doc.iter_sections('notes'))) == 1


def test_examples_are_inherited_whole():
    def target():
        """T."""

    doc = run(target, Operation('examples', sources=(four_returns,)))
    assert doc.section('examples').text == ('>>> four_returns()',)


def test_the_rightmost_source_supplies_a_prose_section():
    def first():
        """F.

        Notes
        -----
        From first.
        """

    def second():
        """S.

        Notes
        -----
        From second.
        """

    def target():
        """T."""

    doc = run(target, Operation('notes', sources=(first, second)))
    assert doc.section('notes').text == ('From second.',)


# Section 56: opaque sections ################################################


def test_an_opaque_section_is_inherited_when_asked_for():
    def target():
        """T."""

    doc = run(
        target, Operation(None, name='Efferents', sources=(four_returns,))
    )
    assert doc.section('Efferents').text == ('Downstream connections.',)


def test_an_opaque_section_is_not_replaced_when_present():
    def target():
        """T.

        Efferents
        ---------
        My own efferents.
        """

    doc = run(
        target, Operation(None, name='Efferents', sources=(four_returns,))
    )
    assert doc.section('Efferents').text == ('My own efferents.',)


def test_an_opaque_section_lookup_ignores_case():
    def target():
        """T."""

    doc = run(
        target, Operation(None, name='efferents', sources=(four_returns,))
    )
    assert doc.section('Efferents') is not None


def test_an_absent_opaque_section_is_simply_not_inherited():
    def target():
        """T."""

    doc = run(
        target, Operation(None, name='Afferents', sources=(four_returns,))
    )
    assert doc.section('Afferents') is None


# Section 61.8: unknown sections are not implicitly inherited ################


def test_an_opaque_section_is_not_inherited_by_an_ordinary_operation():
    def target(x, y):
        """T."""

    doc = run(target, Operation('parameters', sources=(four_returns,)))
    assert doc.section('Efferents') is None


# Errors #####################################################################


def test_binding_a_source_to_an_item_it_lacks_is_an_error():
    def target():
        """T."""

    with pytest.raises(DocMappingError, match='does not document'):
        run(
            target,
            Operation('returns', sources=((four_returns, 'nope'),)),
        )


def test_a_bound_return_replaces_by_position():
    def other():
        """O.

        Returns
        -------
        float
            From other.
        """

    def target():
        """T."""

    doc = run(
        target,
        Operation('returns', sources=(four_returns, (other, 0))),
    )
    assert descriptions(doc, 'returns')[0] == 'From other.'


# Multiple operations ########################################################


def test_several_sections_compose_independently():
    def target(x, y):
        """T."""

    doc = run(
        target,
        Operation('parameters', sources=(alpha,)),
        Operation('returns', sources=(four_returns,)),
        Operation('notes', sources=(four_returns,)),
    )
    assert names(doc) == [('x',), ('y',)]
    assert len(doc.section('returns').items) == 4
    assert doc.section('notes') is not None


def test_no_operations_leaves_the_document_alone():
    def target(x, y):
        """T.

        Parameters
        ----------
        x : int
            The x.
        """

    doc = run(target)
    assert names(doc) == [('x',)]


def test_a_source_with_no_such_section_contributes_nothing():
    def target(x, y):
        """T."""

    doc = run(target, Operation('returns', sources=(alpha,)))
    assert doc.section('returns') is None


# Section 35: composition captures the source at the time it runs ############


def test_composition_uses_the_sources_composed_documentation():
    # A source that was itself composed offers everything it assembled, not
    # only what its own docstring said.
    def base(x, y):
        """B.

        Parameters
        ----------
        x : int
            Base x.
        y : int
            Base y.
        """

    def middle(x, y):
        """M."""

    composed = compose(
        middle, docparse(middle), [Operation('parameters', sources=(base,))]
    )
    from docshare._cache import set_docinfo

    set_docinfo(middle, composed)

    def leaf(x, y):
        """L."""

    doc = run(leaf, Operation('parameters', sources=(middle,)))
    assert descriptions(doc) == ['Base x.', 'Base y.']


# Coverage of the remaining paths ############################################


def wide_group(x, y, z, w):
    """Wide group.

    Parameters
    ----------
    x, y, z : float
        Three at once.
    w : int
        The w.
    """


def test_a_group_error_lists_several_missing_names():
    def target(x, w):
        """T."""

    with pytest.raises(DocInheritanceError) as info:
        run(target, Operation('parameters', sources=(wide_group,)))
    message = str(info.value)
    assert "'y'" in message
    assert "'z'" in message
    assert ' and ' in message


def test_a_parameter_no_source_documents_is_left_alone():
    def target(x, y, w):
        """T."""

    doc = run(target, Operation('parameters', sources=(alpha,)))
    assert names(doc) == [('x',), ('y',)]


def test_binding_a_named_source_item_the_source_lacks_is_an_error():
    def target(x, y):
        """T."""

    with pytest.raises(DocMappingError, match='bound to a specific source'):
        run(target, Operation('parameters', sources=(alpha, (gamma, 'x'))))


def test_a_binding_is_ignored_for_other_items():
    def target(x, y):
        """T."""

    doc = run(target, Operation('parameters', sources=(alpha, (beta, 'x'))))
    assert descriptions(doc) == ['x from beta.', 'y from alpha.']


def test_a_bound_source_item_is_found_by_its_type_label():
    def other():
        """O.

        Raises
        ------
        ValueError
            From other.
        """

    def target():
        """T."""

    doc = run(
        target,
        Operation('raises', sources=(four_returns, (other, 'ValueError'))),
    )
    assert descriptions(doc, 'raises')[0] == 'From other.'


def test_a_bound_item_absent_from_the_inherited_list_is_appended():
    def other():
        """O.

        Raises
        ------
        KeyError
            From other.
        """

    def target():
        """T."""

    doc = run(
        target,
        Operation('raises', sources=(four_returns, (other, 'KeyError'))),
    )
    assert [i.type for i in doc.section('raises').items] == [
        'ValueError',
        'TypeError',
        'KeyError',
    ]


def test_a_named_target_return_may_be_mapped_by_name():
    def source():
        """S.

        Returns
        -------
        sum : float
            Source sum.
        count : int
            Source count.
        """

    def target():
        """T.

        Returns
        -------
        total : float
            My total.
        """

    doc = run(
        target,
        Operation('returns', sources=(source,), mapping={'total': 'sum'}),
    )
    assert descriptions(doc, 'returns') == ['My total.', 'Source count.']
    assert names(doc, 'returns') == [('total',), ('count',)]


def test_a_named_target_return_with_no_counterpart_is_appended():
    def source():
        """S.

        Returns
        -------
        count : int
            Source count.
        """

    def target():
        """T.

        Returns
        -------
        total : float
            My total.
        """

    doc = run(target, Operation('returns', sources=(source,)))
    assert names(doc, 'returns') == [('count',), ('total',)]


def test_a_prose_section_absent_from_every_source_is_not_created():
    def target():
        """T."""

    doc = run(target, Operation('notes', sources=(alpha,)))
    assert doc.section('notes') is None


def test_composing_collapses_duplicate_sections_of_one_kind():
    # A document can hold two sections of the same kind; composition puts
    # the result in the first and drops the rest.
    target_doc = Document(
        summary='T.',
        sections=[
            Section(
                name='Parameters',
                kind='parameters',
                items=[Item(names='x', description='Mine.')],
            ),
            Section(
                name='Parameters',
                kind='parameters',
                items=[Item(names='y', description='Also mine.')],
            ),
        ],
        format='numpy',
    )

    def target(x, y):
        pass

    doc = compose(
        target, target_doc, [Operation('parameters', sources=(alpha,))]
    )
    assert len(list(doc.iter_sections('parameters'))) == 1
    assert names(doc) == [('x',), ('y',)]


def test_label_is_undefined_for_a_name_identified_section():
    from docshare._inherit import _label
    from docshare._sections import IDENTITY_NAME

    assert _label(Item(names='x', type='int'), IDENTITY_NAME) is None


def test_a_prose_section_is_inherited_past_other_sections():
    def target(x, y):
        """T.

        Parameters
        ----------
        x : int
            The x.
        """

    doc = run(target, Operation('notes', sources=(four_returns,)))
    assert doc.section('notes').text == ('A note from the source.',)


def test_an_opaque_section_is_inherited_past_other_sections():
    def target(x, y):
        """T.

        Parameters
        ----------
        x : int
            The x.
        """

    doc = run(
        target, Operation(None, name='Efferents', sources=(four_returns,))
    )
    assert doc.section('Efferents').text == ('Downstream connections.',)


# A position bound to a name-identified section (docs/deferred.md item 11) ###


def test_a_position_bound_to_a_named_section_is_rejected():
    def target(x, y):
        """T."""

    with pytest.raises(DocMappingError, match='identified by name'):
        run(target, Operation('parameters', sources=((alpha, 0),)))


def test_the_rejection_survives_the_source_also_being_given_plainly():
    # This form looks like it works, because the plain source contributes;
    # the binding is dead and used to say nothing.
    def target(x, y):
        """T."""

    with pytest.raises(DocMappingError, match='identified by name'):
        run(target, Operation('parameters', sources=(alpha, (alpha, 0))))


def test_the_rejection_names_the_section_and_the_legal_form():
    def target(x, y):
        """T."""

    with pytest.raises(DocMappingError) as info:
        run(target, Operation('parameters', sources=((alpha, 0),)))
    message = str(info.value)
    assert 'parameters' in message
    assert '(source, "x")' in message
    assert 'Returns' in message


def test_other_name_identified_sections_reject_a_position_too():
    def target():
        """T."""

    with pytest.raises(DocMappingError, match='attributes'):
        run(target, Operation('attributes', sources=((four_returns, 0),)))


def test_a_name_binding_is_still_accepted():
    def target(x, y):
        """T."""

    doc = run(target, Operation('parameters', sources=(gamma, (alpha, 'x'))))
    assert descriptions(doc) == ['x from alpha.', 'y from gamma.']


def test_a_position_bound_to_an_index_identified_section_is_legal():
    def target():
        """T."""

    doc = run(target, Operation('returns', sources=((four_returns, 2),)))
    assert descriptions(doc, 'returns') == ['Third.']


def test_a_label_bound_to_an_index_identified_section_is_legal():
    def target():
        """T."""

    doc = run(
        target, Operation('raises', sources=((four_returns, 'TypeError'),))
    )
    assert [i.type for i in doc.section('raises').items] == ['TypeError']


# The summary and the description ############################################


def summarized(x):
    """The source summary.

    The source description, which is the prose beneath the summary.

    Parameters
    ----------
    x : int
        The x.
    """


def test_a_summary_operation_takes_the_sources_summary():
    def target(x):
        pass

    doc = run(target, Operation(SUMMARY, sources=(summarized,)))
    assert doc.summary == 'The source summary.'
    assert doc.description == ()


def test_a_description_operation_takes_the_sources_description():
    def target(x):
        pass

    doc = run(target, Operation(DESCRIPTION, sources=(summarized,)))
    assert doc.summary is None
    assert 'The source description' in doc.description[0]


def test_a_summary_operation_keeps_the_targets_own_summary():
    def target(x):
        """T."""

    doc = run(target, Operation(SUMMARY, sources=(summarized,)))
    assert doc.summary == 'T.'


def test_a_description_operation_keeps_the_targets_own_description():
    def target(x):
        """T.

        The target's own description.
        """

    doc = run(target, Operation(DESCRIPTION, sources=(summarized,)))
    assert doc.description == ("The target's own description.",)


def test_a_section_operation_leaves_the_summary_alone():
    def target(x):
        pass

    doc = run(target, Operation('parameters', sources=(summarized,)))
    assert doc.summary is None
    assert doc.description == ()
    assert descriptions(doc) == ['The x.']


def test_the_components_are_named_apart_from_every_section():
    # A section kind or an opaque title could otherwise collide with them.
    for component in (SUMMARY, DESCRIPTION):
        assert section_kind(component) is None
        assert not component[0].isalnum()
