# -*- coding: utf-8 -*-
"""Tests for validating documented parameters against signatures."""

import pytest

from docshare import (
    DocMappingError,
    DocSignatureError,
    Document,
    Item,
    Section,
    docparse,
)
from docshare._sections import custom_kind
from docshare._signature import (
    _describe,
    _display,
    as_names,
    documented_parameters,
    parameter_names,
    signature_of,
    strip_stars,
    validate_signature,
)


def document(*names, section='Parameters', underline='----------'):
    """Build a document whose Parameters section declares `names`."""
    lines = ['S.', '', section, underline]
    for name in names:
        lines.append(f'{name} : int')
        lines.append('    A parameter.')
    return docparse('\n'.join(lines))


def check(obj, *names, **kwargs):
    """Validate `obj` against a document declaring `names`."""
    validate_signature(obj, document(*names), **kwargs)


# Helpers ####################################################################


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (None, ()),
        ('x', ('x',)),
        (('x', 'y'), ('x', 'y')),
        (['x'], ('x',)),
        (iter(['x', 'y']), ('x', 'y')),
    ],
)
def test_as_names(value, expected):
    assert as_names(value) == expected


@pytest.mark.parametrize(
    ('written', 'expected'),
    [('x', 'x'), ('*args', 'args'), ('**kwargs', 'kwargs')],
)
def test_strip_stars(written, expected):
    assert strip_stars(written) == expected


def test_documented_parameters_reports_every_name():
    doc = document('x', 'y')
    assert [name for (_, _, name) in documented_parameters(doc)] == ['x', 'y']


def test_documented_parameters_expands_a_group():
    doc = docparse('S.\n\nParameters\n----------\nx, y : int\n    Both.\n')
    assert [name for (_, _, name) in documented_parameters(doc)] == ['x', 'y']


def test_documented_parameters_ignores_other_sections():
    doc = docparse('S.\n\nReturns\n-------\nresult : int\n    The result.\n')
    assert list(documented_parameters(doc)) == []


def test_documented_parameters_covers_other_parameters():
    doc = docparse(
        'S.\n\nOther Parameters\n----------------\nx : int\n    The x.\n'
    )
    assert [name for (_, _, name) in documented_parameters(doc)] == ['x']


def test_documented_parameters_covers_keyword_arguments():
    doc = docparse('S.\n\nKeyword Args:\n    x (int): The x.\n')
    assert [name for (_, _, name) in documented_parameters(doc)] == ['x']


def test_display_falls_back_to_name_without_a_qualname():
    import inspect as module

    assert not hasattr(module, '__qualname__')
    assert _display(module) == 'inspect'


def test_display_falls_back_to_repr():
    assert _display(5) == '5'


def test_describe_omits_a_signature_it_cannot_determine():
    assert _describe(5) == '5'


def test_describe_includes_the_signature_when_there_is_one():
    def f(x, y=1):
        pass

    # __qualname__ locates a nested function, which is what makes the
    # message useful for a method.
    assert _describe(f).endswith('f(x, y=1)')
    assert '<locals>' in _describe(f)


def test_describe_uses_the_qualified_name_of_a_method():
    assert _describe(Example.method) == 'Example.method(self, x)'


# Parameter kinds ############################################################


def test_positional_or_keyword_parameters():
    def f(x, y=1):
        pass

    check(f, 'x', 'y')


def test_positional_only_parameters():
    def f(x, y, /, z):
        pass

    check(f, 'x', 'y', 'z')


def test_keyword_only_parameters():
    def f(*, x, y=1):
        pass

    check(f, 'x', 'y')


def test_var_positional_documented_with_stars():
    def f(*args):
        pass

    check(f, '*args')


def test_var_positional_documented_without_stars():
    def f(*args):
        pass

    check(f, 'args')


def test_var_keyword_documented_with_stars():
    def f(**kwargs):
        pass

    check(f, '**kwargs')


def test_every_parameter_kind_at_once():
    def f(a, /, b, *args, c, **kwargs):
        pass

    check(f, 'a', 'b', '*args', 'c', '**kwargs')


def test_a_grouped_declaration_validates_each_name():
    def f(x, y):
        pass

    doc = docparse('S.\n\nParameters\n----------\nx, y : int\n    Both.\n')
    validate_signature(f, doc)


def test_a_grouped_declaration_reports_the_bad_name():
    def f(x):
        pass

    doc = docparse('S.\n\nParameters\n----------\nx, y : int\n    Both.\n')
    with pytest.raises(DocSignatureError, match="'y'"):
        validate_signature(f, doc)


def test_the_error_locates_the_grouped_declaration():
    def f(x):
        pass

    doc = docparse('S.\n\nParameters\n----------\nx, y : int\n    Both.\n')
    with pytest.raises(DocSignatureError) as info:
        validate_signature(f, doc)
    assert "grouped declaration 'x, y'" in str(info.value)


# Partial documentation ######################################################


def test_undocumented_parameters_are_allowed():
    def f(x, y, z):
        pass

    check(f, 'x')


def test_documenting_nothing_is_allowed():
    def f(x, y):
        pass

    validate_signature(f, Document())


def test_self_need_not_be_documented():
    class C:
        def m(self, x):
            pass

    check(C.m, 'x')


def test_self_may_be_documented():
    class C:
        def m(self, x):
            pass

    check(C.m, 'self', 'x')


# Failures ###################################################################


def test_an_undeclared_parameter_is_an_error():
    def f(x):
        pass

    with pytest.raises(DocSignatureError, match="'scale'"):
        check(f, 'scale')


def test_a_kwargs_signature_does_not_excuse_an_undeclared_parameter():
    # These must be declared rather than inferred, since **kwargs would
    # otherwise excuse every possible typo.
    def f(**kwargs):
        pass

    with pytest.raises(DocSignatureError, match="'null'"):
        check(f, 'null')


def test_the_error_names_the_object_and_its_signature():
    def f(x, y=1):
        pass

    with pytest.raises(DocSignatureError) as info:
        check(f, 'scale')
    message = str(info.value)
    assert 'f(x, y=1)' in message
    assert "'Parameters'" in message


def test_the_error_suggests_extraparam():
    def f(x):
        pass

    with pytest.raises(DocSignatureError) as info:
        check(f, 'null')
    assert "extraparam='null'" in str(info.value)


def test_the_error_names_the_section_it_came_from():
    def f(x):
        pass

    doc = docparse(
        'S.\n\nOther Parameters\n----------------\nz : int\n    The z.\n'
    )
    with pytest.raises(DocSignatureError, match="'Other Parameters'"):
        validate_signature(f, doc)


def test_a_duplicated_parameter_is_an_error():
    def f(x):
        pass

    doc = docparse(
        'S.\n\n'
        'Parameters\n----------\nx : int\n    The x.\n\n'
        'Other Parameters\n----------------\nx : int\n    Again.\n'
    )
    with pytest.raises(DocSignatureError, match='more than once'):
        validate_signature(f, doc)


def test_the_duplicate_error_names_both_sections():
    def f(x):
        pass

    doc = docparse(
        'S.\n\n'
        'Parameters\n----------\nx : int\n    The x.\n\n'
        'Other Parameters\n----------------\nx : int\n    Again.\n'
    )
    with pytest.raises(DocSignatureError) as info:
        validate_signature(f, doc)
    assert "'Parameters'" in str(info.value)
    assert "'Other Parameters'" in str(info.value)


# extraparam #################################################################


def test_extraparam_accepts_a_single_name():
    def f(**kwargs):
        pass

    check(f, 'null', extraparam='null')


def test_extraparam_accepts_a_sequence():
    def f(**kwargs):
        pass

    check(f, 'null', 'void', extraparam=('null', 'void'))


def test_extraparam_may_be_written_with_stars():
    def f(x):
        pass

    check(f, 'extra', extraparam='*extra')


def test_extraparam_does_not_excuse_other_names():
    def f(**kwargs):
        pass

    with pytest.raises(DocSignatureError, match="'void'"):
        check(f, 'null', 'void', extraparam='null')


# parammap ###################################################################


def test_parammap_keys_must_name_real_parameters():
    def f(x):
        pass

    with pytest.raises(DocMappingError, match="'nope'"):
        check(f, 'x', parammap={'nope': 'y'})


def test_parammap_keys_may_be_undocumented_parameters():
    # A mapped parameter need not be documented by the target; that is the
    # usual case, since the documentation is what is being inherited.
    def f(x, y):
        pass

    check(f, 'x', parammap={'y': 'other'})


def test_parammap_keys_may_be_declared_through_extraparam():
    def f(**kwargs):
        pass

    check(f, parammap={'null': 'other'}, extraparam='null')


def test_the_parammap_error_explains_the_direction():
    def f(x):
        pass

    with pytest.raises(DocMappingError) as info:
        check(f, 'x', parammap={'nope': 'y'})
    message = str(info.value)
    assert 'parameters of the object being documented' in message
    assert 'source' in message


def test_an_empty_parammap_is_harmless():
    def f(x):
        pass

    check(f, 'x', parammap={})


# Object types ###############################################################


class Example:
    """Example."""

    def __init__(self, a, b=1):
        pass

    def method(self, x):
        pass

    @staticmethod
    def static(p):
        pass

    @classmethod
    def klass(cls, r):
        pass

    @property
    def prop(self):
        return 1


def test_a_class_validates_against_its_initializer():
    check(Example, 'a', 'b')


def test_a_class_rejects_a_parameter_its_initializer_lacks():
    with pytest.raises(DocSignatureError, match="'c'"):
        check(Example, 'c')


def test_a_method_validates():
    check(Example.method, 'x')


def test_a_bound_method_validates_without_self():
    check(Example(1).method, 'x')


def test_a_staticmethod_object_validates():
    check(Example.__dict__['static'], 'p')


def test_a_classmethod_object_validates():
    # inspect.signature cannot handle a classmethod object directly, so the
    # underlying function is used; cls is therefore an accepted name.
    check(Example.__dict__['klass'], 'r')


def test_a_classmethod_object_rejects_an_unknown_parameter():
    with pytest.raises(DocSignatureError, match="'zzz'"):
        check(Example.__dict__['klass'], 'zzz')


def test_a_property_validates_against_its_getter():
    check(Example.__dict__['prop'], 'self')


# Objects without signatures #################################################


@pytest.mark.parametrize('obj', [5, 'text', (1, 2), Example(1)])
def test_objects_without_signatures_are_skipped(obj):
    assert parameter_names(obj) is None
    assert signature_of(obj) is None
    check(obj, 'anything')


def test_a_write_only_property_has_no_signature():
    prop = property(None, lambda self, value: None)
    assert signature_of(prop) is None
    check(prop, 'anything')


# Declared sections are not the callable's parameters #########################


def test_a_declared_section_is_not_checked_against_the_signature():
    # "Inputs" documents observed data, not arguments, so a name that is not
    # a parameter is correct rather than a mistake. This is what keeps the
    # motivating docstring legal.
    inputs = custom_kind('Inputs', 'Parameters')

    def model(w):
        pass

    doc = Document(
        summary='Fit a model.',
        sections=(
            Section(
                name='Parameters',
                kind='parameters',
                items=(Item(names=('w',), description=('The weights.',)),),
            ),
            Section(
                name='Inputs',
                custom=inputs,
                items=(Item(names=('x',), description=('The data.',)),),
            ),
        ),
        format='numpy',
    )
    validate_signature(model, doc)


def test_what_it_resembles_is_still_checked():
    # Only the declared section is exempt; the real Parameters section is
    # validated exactly as before.
    def model(w):
        pass

    doc = Document(
        summary='Fit a model.',
        sections=(
            Section(
                name='Parameters',
                kind='parameters',
                items=(Item(names=('nope',), description=('No.',)),),
            ),
        ),
        format='numpy',
    )
    with pytest.raises(DocSignatureError, match='no such parameter'):
        validate_signature(model, doc)
