# -*- coding: utf-8 -*-
"""Tests for the docwrap decorator."""

import functools
import pydoc

import pytest

from docshare import (
    DocFormatError,
    DocInheritanceError,
    DocMappingError,
    DocShareError,
    DocSignatureError,
    _decorator,
    clear_docinfo,
    docinfo,
    docwrap,
)
from docshare._decorator import (
    SECTION_ARGUMENTS,
    _operations,
    _Sources,
)
from docshare._model import Document


@pytest.fixture(autouse=True)
def _empty_cache():
    clear_docinfo()
    yield
    clear_docinfo()


def source(foo, bar=1):
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

    Raises
    ------
    ValueError
        If bad.

    Notes
    -----
    A note from the source.

    Efferents
    ---------
    Downstream connections.
    """


# The guiding example ########################################################


def test_the_readme_example():
    @docwrap(format='numpy')
    def quuxatize(foo, bar=1):
        """A function that quuxizes the arguments `foo` and `bar`.

        Parameters
        ----------
        foo : float
            The foo parameter for the quux operation.
        bar : float, optional
            The bar parameter for the quux operation; the default is 1.

        Returns
        -------
        float
            The quux result.
        """

    @docwrap(format='numpy', inheritparams=quuxatize)
    def logquuxatize(foo, bar=1, base=None):
        """Returns the log of the quux of arguments `foo` and `bar`.

        Parameters
        ----------
        base : float, optional
            The base of the log that should be used; the default is
            ``None``.

        Returns
        -------
        float
            The log-quux result.
        """

    assert logquuxatize.__doc__ == (
        'Returns the log of the quux of arguments `foo` and `bar`.\n'
        '\n'
        'Parameters\n'
        '----------\n'
        'foo : float\n'
        '    The foo parameter for the quux operation.\n'
        'bar : float, optional\n'
        '    The bar parameter for the quux operation; the default is 1.\n'
        'base : float, optional\n'
        '    The base of the log that should be used; the default is\n'
        '    ``None``.\n'
        '\n'
        'Returns\n'
        '-------\n'
        'float\n'
        '    The log-quux result.'
    )


# Calling conventions ########################################################


def test_the_decorator_may_be_used_bare():
    @docwrap
    def f(x):
        """F.

        Parameters
        ----------
        x : int
            The x.
        """

    assert f.__doc__.startswith('F.')
    assert docinfo(f).section('parameters') is not None


def test_the_decorator_may_be_called_directly():
    def f(foo, bar=1):
        """F."""

    assert docwrap(f, format='numpy', inheritparams=source) is f
    assert 'The foo parameter.' in f.__doc__


def test_the_decorator_returns_the_same_object():
    def f(x):
        """F."""

    assert docwrap(format='numpy')(f) is f


# Section 61.10: composition happens once ####################################


def test_a_docstring_is_left_alone_when_nothing_is_inherited():
    original = """F.

    Parameters
    ----------
    x    :   int
        Deliberately odd spacing.
    """

    def f(x):
        pass

    f.__doc__ = original
    docwrap(f)
    assert f.__doc__ == original


def test_the_parsed_document_is_recorded_even_without_inheritance():
    def f(x):
        """F.

        Parameters
        ----------
        x : int
            The x.
        """

    docwrap(f)
    assert docinfo(f) is docinfo(f)
    assert docinfo(f).section('parameters') is not None


def test_the_composed_document_is_recorded():
    def f(foo, bar=1):
        """F."""

    docwrap(f, format='numpy', inheritparams=source)
    recorded = docinfo(f)
    assert [i.names for i in recorded.section('parameters').items] == [
        ('foo',),
        ('bar',),
    ]


def test_a_composed_object_can_itself_be_inherited_from():
    def middle(foo, bar=1):
        """M."""

    docwrap(middle, format='numpy', inheritparams=source)

    def leaf(foo, bar=1):
        """L."""

    docwrap(leaf, format='numpy', inheritparams=middle)
    assert 'The foo parameter.' in leaf.__doc__


def test_a_later_change_to_a_source_does_not_propagate():
    def upstream(x):
        """U.

        Parameters
        ----------
        x : int
            Original.
        """

    def target(x):
        """T."""

    docwrap(target, format='numpy', inheritparams=upstream)
    assert 'Original.' in target.__doc__
    upstream.__doc__ = 'U.\n\nParameters\n----------\nx : int\n    Changed.\n'
    assert 'Original.' in target.__doc__


# Object types and decorator ordering ########################################


def base_method(self, x):
    """Base.

    Parameters
    ----------
    x : int
        The x from base.
    """


def base_static(p):
    """Base static.

    Parameters
    ----------
    p : int
        The p from base.
    """


def base_property(self):
    """Base property.

    Returns
    -------
    int
        The value from base.
    """


class Example:
    """Example class.

    Attributes
    ----------
    value : int
        The value.
    """

    @docwrap(format='numpy', inheritparams=base_method)
    def method(self, x):
        pass

    @docwrap(format='numpy', inheritparams=base_static)
    @staticmethod
    def static_above(p):
        pass

    @staticmethod
    @docwrap(format='numpy', inheritparams=base_static)
    def static_below(p):
        pass

    @docwrap(format='numpy', inheritparams=base_static)
    @classmethod
    def class_above(cls, p):
        pass

    @classmethod
    @docwrap(format='numpy', inheritparams=base_static)
    def class_below(cls, p):
        pass

    @docwrap(format='numpy', inheritreturns=base_property)
    @property
    def property_above(self):
        pass

    @property
    @docwrap(format='numpy', inheritreturns=base_property)
    def property_below(self):
        pass


@pytest.mark.parametrize(
    'name',
    [
        'method',
        'static_above',
        'static_below',
        'class_above',
        'class_below',
        'property_above',
        'property_below',
    ],
)
def test_every_descriptor_ordering_composes(name):
    assert 'from base' in Example.__dict__[name].__doc__


@pytest.mark.parametrize(
    ('name', 'kind'),
    [
        ('static_above', staticmethod),
        ('static_below', staticmethod),
        ('class_above', classmethod),
        ('class_below', classmethod),
        ('property_above', property),
        ('property_below', property),
    ],
)
def test_descriptors_keep_their_type(name, kind):
    assert isinstance(Example.__dict__[name], kind)


def test_descriptors_remain_usable():
    instance = Example()
    assert callable(Example.static_below)
    assert callable(Example.class_below)
    assert instance.property_below is None


def test_a_class_can_be_decorated():
    def base(x):
        """B.

        Attributes
        ----------
        value : int
            The value from base.
        """

    @docwrap(format='numpy', inheritattributes=base)
    class Target:
        """T."""

    assert 'The value from base.' in Target.__doc__


def test_functools_wraps_carries_the_composed_documentation():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inheritparams=source)

    @functools.wraps(target)
    def wrapper(*args, **kwargs):
        return target(*args, **kwargs)

    assert wrapper.__doc__ == target.__doc__


# Section 57: the result is ordinary documentation ###########################


def test_help_shows_the_composed_documentation():
    def f(foo, bar=1):
        """F."""

    docwrap(f, format='numpy', inheritparams=source)
    rendered = pydoc.render_doc(f)
    assert 'The foo parameter.' in rendered


def test_the_docstring_is_a_plain_string():
    def f(foo, bar=1):
        """F."""

    docwrap(f, format='numpy', inheritparams=source)
    assert type(f.__doc__) is str


# Generalized and bulk interfaces ############################################


def test_the_generalized_inherit_argument():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inherit={'Parameters': source})
    assert 'The foo parameter.' in target.__doc__


def test_the_generalized_inherit_accepts_a_kind_name():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inherit={'parameters': source})
    assert 'The foo parameter.' in target.__doc__


def test_the_generalized_inherit_rejects_an_unknown_section():
    def target(foo, bar=1):
        """T."""

    with pytest.raises(DocShareError, match='inheritother'):
        docwrap(target, format='numpy', inherit={'Efferents': source})


def test_naming_a_section_twice_is_an_error():
    def target(foo, bar=1):
        """T."""

    with pytest.raises(DocShareError, match='one place or the other'):
        docwrap(
            target,
            format='numpy',
            inherit={'Parameters': source},
            inheritparams=source,
        )


def test_inheritall_takes_every_recognized_section():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inheritall=source)
    assert 'The foo parameter.' in target.__doc__
    assert 'The quux.' in target.__doc__
    assert 'If bad.' in target.__doc__
    assert 'A note from the source.' in target.__doc__


def described(foo, bar=1):
    """Compute a described quux.

    The long account of what a described quux is, which is the description
    rather than the summary.

    Parameters
    ----------
    foo : float
        The foo parameter.
    bar : float, optional
        The bar parameter; the default is 1.
    """


def test_inheritall_takes_the_summary_and_the_description():
    def target(foo, bar=1):
        pass

    docwrap(target, format='numpy', inheritall=described)
    assert target.__doc__.startswith('Compute a described quux.')
    assert 'The long account' in target.__doc__
    assert 'The foo parameter.' in target.__doc__


def test_inheritsummary_takes_only_the_summary():
    def target(foo, bar=1):
        pass

    docwrap(target, format='numpy', inheritsummary=described)
    assert target.__doc__ == 'Compute a described quux.'


def test_inheritdescription_takes_only_the_description():
    def target(foo, bar=1):
        pass

    docwrap(target, format='numpy', inheritdescription=described)
    assert 'The long account' in target.__doc__
    assert 'Compute a described quux.' not in target.__doc__


def test_the_targets_own_summary_is_kept():
    def target(foo, bar=1):
        """Our own summary."""

    docwrap(target, format='numpy', inheritall=described)
    assert target.__doc__.startswith('Our own summary.')
    assert 'Compute a described quux.' not in target.__doc__
    # The description is the target's own too: it has none, so it takes one.
    assert 'The long account' in target.__doc__


def test_the_targets_own_description_is_kept():
    def target(foo, bar=1):
        """Our own summary.

        Our own description.
        """

    docwrap(target, format='numpy', inheritall=described)
    assert 'Our own description.' in target.__doc__
    assert 'The long account' not in target.__doc__


def test_inheriting_a_section_does_not_take_the_summary():
    def target(foo, bar=1):
        pass

    docwrap(target, format='numpy', inheritparams=described)
    assert 'Compute a described quux.' not in target.__doc__
    assert 'The foo parameter.' in target.__doc__


def test_the_summary_comes_from_the_last_source_that_has_one():
    def bare(foo, bar=1):
        pass

    def target(foo, bar=1):
        pass

    docwrap(target, format='numpy', inheritsummary=(described, bare))
    assert target.__doc__ == 'Compute a described quux.'


def test_inheritsummary_from_a_source_without_one_does_nothing():
    def bare(foo, bar=1):
        pass

    def target(foo, bar=1):
        pass

    docwrap(target, format='numpy', inheritsummary=bare, inheritparams=source)
    assert target.__doc__.startswith('Parameters')


def test_inheritsummary_accepts_a_parsed_document():
    def target(foo, bar=1):
        pass

    docwrap(
        target,
        format='numpy',
        inheritsummary=docinfo(described, format='numpy'),
    )
    assert target.__doc__ == 'Compute a described quux.'


def test_inheritall_leaves_unrecognized_sections_alone():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inheritall=source)
    assert 'Efferents' not in target.__doc__


def test_inheritall_with_inheritother_takes_unrecognized_sections_too():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inheritall=source, inheritother=True)
    assert 'Downstream connections.' in target.__doc__


def test_inheritother_takes_a_named_section():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inheritother=[(source, 'Efferents')])
    assert 'Downstream connections.' in target.__doc__
    assert 'The foo parameter.' not in target.__doc__


def test_inheritother_rejects_a_bare_source():
    def target(foo, bar=1):
        """T."""

    with pytest.raises(DocShareError, match='section name'):
        docwrap(target, format='numpy', inheritother=[source])


# Arguments ##################################################################


@pytest.mark.parametrize(
    'name',
    [
        'inheritparams',
        'inheritreturns',
        'inheritraises',
        'inherityields',
        'inheritattributes',
        'inheritexamples',
        'inheritnotes',
        'inheritwarnings',
    ],
)
def test_section_22_names_all_exist(name):
    assert name in SECTION_ARGUMENTS


@pytest.mark.parametrize(
    'name',
    [
        'dropparams',
        'parammap',
        'ignorereturns',
        'returnmap',
        'ignoreraises',
        'raisemap',
        'ignoreattributes',
        'attributemap',
        'dropotherparams',
        'otherparammap',
        'dropkeywordargs',
        'keywordargmap',
    ],
)
def test_section_42_naming_is_consistent(name):
    assert name in SECTION_ARGUMENTS


# Excluding items: drop names yours, ignore names the source's #############


@pytest.mark.parametrize(
    'kind', ['parameters', 'other_parameters', 'keyword_arguments']
)
def test_parameter_sections_offer_drop_not_ignore(kind):
    short = {
        'parameters': 'params',
        'other_parameters': 'otherparams',
        'keyword_arguments': 'keywordargs',
    }[kind]
    assert f'drop{short}' in SECTION_ARGUMENTS
    assert f'ignore{short}' not in SECTION_ARGUMENTS


@pytest.mark.parametrize(
    'short',
    [
        'returns',
        'yields',
        'receives',
        'raises',
        'warns',
        'attributes',
        'methods',
    ],
)
def test_source_driven_sections_offer_ignore_not_drop(short):
    assert f'ignore{short}' in SECTION_ARGUMENTS
    assert f'drop{short}' not in SECTION_ARGUMENTS


def test_ignoreparams_is_rejected_and_names_dropparams():
    def f(x):
        """F."""

    with pytest.raises(DocShareError, match='use dropparams='):
        docwrap(f, ignoreparams='x')


def test_dropreturns_is_rejected_and_names_ignorereturns():
    def f(x):
        """F."""

    with pytest.raises(DocShareError, match='use ignorereturns='):
        docwrap(f, dropreturns=0)


def test_the_wrong_prefix_error_explains_which_side_is_meant():
    def f(x):
        """F."""

    with pytest.raises(DocShareError) as info:
        docwrap(f, ignoreparams='x')
    assert 'ordered by the signature' in str(info.value)
    with pytest.raises(DocShareError) as info:
        docwrap(f, dropattributes='x')
    assert 'driven by its sources' in str(info.value)


@pytest.mark.parametrize(
    ('wrong', 'right'),
    [
        ('ignoreparams', 'dropparams'),
        ('ignoreotherparams', 'dropotherparams'),
        ('ignorekeywordargs', 'dropkeywordargs'),
        ('dropreturns', 'ignorereturns'),
        ('dropyields', 'ignoreyields'),
        ('dropraises', 'ignoreraises'),
        ('dropwarns', 'ignorewarns'),
        ('dropattributes', 'ignoreattributes'),
        ('dropmethods', 'ignoremethods'),
        ('dropreceives', 'ignorereceives'),
    ],
)
def test_every_wrong_prefix_names_its_counterpart(wrong, right):
    def f(x):
        """F."""

    with pytest.raises(DocShareError, match=f'use {right}='):
        docwrap(f, **{wrong: 'x'})


def test_a_prefix_mistake_on_a_prose_section_falls_back_to_resemblance():
    # Prose sections have no exclusion at all, so there is no counterpart to
    # name and the ordinary suggestion applies.
    def f(x):
        """F."""

    with pytest.raises(DocShareError, match='did you mean'):
        docwrap(f, dropnotes='x')


# Every parameter section is ordered by the signature ######################


def test_other_parameters_cannot_inherit_a_parameter_the_target_lacks():
    def base(x, y):
        """B.

        Other Parameters
        ----------------
        ghost : int
            Not a parameter of the target.
        y : float
            The y.
        """

    @docwrap(format='numpy', inheritotherparams=base)
    def f(x, y):
        """F."""

    assert 'ghost' not in f.__doc__
    assert 'The y.' in f.__doc__


def test_keyword_args_cannot_inherit_a_parameter_the_target_lacks():
    def base(**kwargs):
        """B.

        Keyword Args:
            ghost (int): Not a parameter of the target.
        """

    @docwrap(format='google', inheritkeywordargs=base)
    def f(**kwargs):
        """F."""

    assert f.__doc__ == 'F.'


def test_other_parameters_follow_the_signature_order():
    def base(x, y):
        """B.

        Other Parameters
        ----------------
        y : float
            The y.
        x : float
            The x.
        """

    @docwrap(format='numpy', inheritotherparams=base)
    def f(x, y):
        """F."""

    assert f.__doc__.index('x : float') < f.__doc__.index('y : float')


def test_extraparam_admits_an_inherited_other_parameter():
    def base(**kwargs):
        """B.

        Other Parameters
        ----------------
        null : bool
            The null.
        """

    @docwrap(format='numpy', inheritotherparams=base, extraparam='null')
    def f(**kwargs):
        """F."""

    assert 'The null.' in f.__doc__


def test_the_composed_document_is_validated():
    # A source-driven section could otherwise document a parameter the
    # target does not have without anything noticing.
    from docshare import Document, Item, Section
    from docshare._decorator import _apply

    def f(x):
        """F."""

    phantom = Document(
        sections=[
            Section(
                name='Parameters',
                kind='parameters',
                items=[Item(names='ghost', description='Nope.')],
            )
        ],
        format='numpy',
    )
    import docshare._decorator as decorator

    original = decorator.compose
    decorator.compose = lambda *a, **k: phantom
    try:
        with pytest.raises(DocSignatureError, match="'ghost'"):
            _apply(f, {'format': 'numpy', 'inheritparams': source})
    finally:
        decorator.compose = original
    assert f.__doc__ == 'F.'


# Maps for source-driven sections ###########################################


def test_attributemap_renames_an_inherited_attribute():
    def base():
        """B.

        Attributes
        ----------
        cache : dict
            The cache.
        """

    @docwrap(
        format='numpy', inheritattributes=base, attributemap={'store': 'cache'}
    )
    class Target:
        """T."""

    assert 'store : dict' in Target.__doc__
    assert 'cache : dict' not in Target.__doc__


def test_attributemap_leaves_unmapped_attributes_alone():
    def base():
        """B.

        Attributes
        ----------
        cache : dict
            The cache.
        other : int
            The other.
        """

    @docwrap(
        format='numpy', inheritattributes=base, attributemap={'store': 'cache'}
    )
    class Target:
        """T."""

    assert 'store : dict' in Target.__doc__
    assert 'other : int' in Target.__doc__


def test_ignoreattributes_names_a_source_attribute():
    def base():
        """B.

        Attributes
        ----------
        cache : dict
            The cache.
        other : int
            The other.
        """

    @docwrap(format='numpy', inheritattributes=base, ignoreattributes='cache')
    class Target:
        """T."""

    assert 'cache' not in Target.__doc__
    assert 'other : int' in Target.__doc__


@pytest.mark.parametrize('name', ['inheritseealso', 'inheritreferences'])
def test_prose_sections_offer_only_inheritance(name):
    assert name in SECTION_ARGUMENTS
    assert f'drop{name[len("inherit") :]}' not in SECTION_ARGUMENTS


def test_an_unknown_argument_is_rejected():
    def f(x):
        """F."""

    with pytest.raises(DocShareError, match='unexpected argument'):
        docwrap(f, inheritnothing=source)


def test_an_unknown_argument_suggests_a_close_match():
    def f(x):
        """F."""

    with pytest.raises(DocShareError, match='inheritparams'):
        docwrap(f, inheritparam=source)


def test_a_misspelled_argument_is_caught_before_any_work():
    original = 'F.'

    def f(x):
        pass

    f.__doc__ = original
    with pytest.raises(DocShareError):
        docwrap(f, dropparam='x')
    assert f.__doc__ == original


# Validation at decoration time ##############################################


def test_signature_validation_runs_at_decoration_time():
    with pytest.raises(DocSignatureError, match="'scal'"):

        @docwrap(format='numpy')
        def f(scale=1):
            """F.

            Parameters
            ----------
            scal : int
                Typo.
            """


def test_extraparam_is_accepted():
    @docwrap(format='numpy', extraparam='null')
    def f(**kwargs):
        """F.

        Parameters
        ----------
        null : bool
            The null.
        """

    assert 'The null.' in f.__doc__


def test_extraparam_participates_in_inheritance():
    def base(**kwargs):
        """B.

        Parameters
        ----------
        null : bool
            The null from base.
        """

    @docwrap(format='numpy', inheritparams=base, extraparam='null')
    def f(**kwargs):
        """F."""

    assert 'The null from base.' in f.__doc__


def test_an_incoherent_inheritance_fails_at_decoration_time():
    def grouped(x, y, z):
        """G.

        Parameters
        ----------
        x, y : float
            Both at once.
        """

    with pytest.raises(DocInheritanceError):

        @docwrap(format='numpy', inheritparams=grouped)
        def f(x, y, z):
            """F.

            Parameters
            ----------
            x : float
                Only one.
            """


# Formats ####################################################################


def test_an_undocumented_target_requires_a_format_to_write_in():
    def f(foo, bar=1):
        pass

    with pytest.raises(DocFormatError, match='render='):
        docwrap(f, inheritparams=source)


def test_an_undocumented_target_composes_with_an_explicit_format():
    def f(foo, bar=1):
        pass

    docwrap(f, format='numpy', inheritparams=source)
    assert f.__doc__.startswith('Parameters')


def test_the_format_is_detected_from_the_targets_own_docstring():
    def f(foo, bar=1):
        """F.

        Args:
            baz (int): The baz.
        """

    def google_source(foo, bar=1):
        """G.

        Args:
            foo (float): The foo from google.
        """

    docwrap(f, inheritparams=google_source, extraparam='baz')
    assert 'foo (float): The foo from google.' in f.__doc__


def test_the_format_argument_still_asserts_how_the_docstring_is_written():
    # format= says what the docstring is written in, per specification
    # section 4.1; it is render= that says how to write the result.
    def f(foo, bar=1):
        """F.

        Parameters
        ----------
        bar : float
            My own bar.
        """

    with pytest.raises(DocFormatError, match='required to be'):
        docwrap(f, format='google', inheritparams=source)


def test_render_converts_a_document_into_the_other_format():
    def f(foo, bar=1):
        """F.

        Parameters
        ----------
        bar : float
            My own bar.
        """

    docwrap(f, format='numpy', render='google', inheritparams=source)
    assert 'Args:' in f.__doc__
    assert 'foo (float): The foo parameter.' in f.__doc__
    assert 'Parameters\n----------' not in f.__doc__


def test_render_alone_writes_an_undocumented_target():
    # There is no docstring to detect a format from, so render= alone says
    # how to write one.
    def f(foo, bar=1):
        pass

    docwrap(f, render='numpy', inheritparams=source)
    assert f.__doc__.startswith('Parameters\n----------')


def test_render_defaults_to_the_detected_format():
    def f(foo, bar=1):
        """F.

        Args:
            bar (float): My own bar.
        """

    docwrap(f, inheritparams=source)
    assert 'Args:' in f.__doc__


def test_render_defaults_to_an_explicit_format():
    def f(foo, bar=1):
        """F.

        Parameters
        ----------
        bar : float
            My own bar.
        """

    docwrap(f, format='numpy', inheritparams=source)
    assert 'Parameters\n----------' in f.__doc__


def test_render_is_rejected_when_unsupported():
    def f(foo, bar=1):
        """F."""

    with pytest.raises(DocFormatError, match='unsupported'):
        docwrap(f, render='rest', inheritparams=source)


def test_a_google_target_may_inherit_from_a_numpy_source():
    # The document model is format-independent, so the source's style is
    # irrelevant; the target is written in its own.
    def f(foo, bar=1):
        """F.

        Args:
            bar (float): My own bar.
        """

    docwrap(f, inheritparams=source)
    assert 'Args:' in f.__doc__
    assert 'foo (float): The foo parameter.' in f.__doc__
    assert 'Parameters\n----------' not in f.__doc__


def test_a_numpy_target_may_inherit_from_a_google_source():
    def google_source(foo, bar=1):
        """G.

        Args:
            foo (float): The foo from google.
        """

    def f(foo, bar=1):
        """F.

        Parameters
        ----------
        bar : float
            My own bar.
        """

    docwrap(f, inheritparams=google_source)
    assert 'Parameters\n----------' in f.__doc__
    assert 'foo : float' in f.__doc__


def test_an_unwritable_docstring_is_reported():
    class Slotted:
        __slots__ = ()

    with pytest.raises(DocShareError, match='not writable'):
        docwrap(Slotted(), format='numpy', inheritparams=source)


# Per-section arguments through the decorator ################################


def test_dropparams_through_the_decorator():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inheritparams=source, dropparams='foo')
    assert 'The foo parameter.' not in target.__doc__
    assert 'The bar parameter' in target.__doc__


def test_dropparams_accepts_several_names():
    def target(foo, bar=1):
        """T.

        Notes
        -----
        Keeps the document from being empty.
        """

    docwrap(
        target,
        format='numpy',
        inheritparams=source,
        dropparams=('foo', 'bar'),
    )
    assert 'The foo parameter.' not in target.__doc__
    assert 'The bar parameter' not in target.__doc__


def test_parammap_through_the_decorator():
    def target(inp, bar=1):
        """T."""

    docwrap(
        target,
        format='numpy',
        inheritparams=source,
        parammap={'inp': 'foo'},
    )
    assert 'inp : float' in target.__doc__
    assert 'The foo parameter.' in target.__doc__


def test_ignorereturns_through_the_decorator():
    def many():
        """M.

        Returns
        -------
        float
            First.
        float
            Second.
        """

    def target():
        """T."""

    docwrap(target, format='numpy', inheritreturns=many, ignorereturns=0)
    assert 'Second.' in target.__doc__
    assert 'First.' not in target.__doc__


def test_returnmap_through_the_decorator():
    def many():
        """M.

        Returns
        -------
        float
            First.
        float
            Second.
        """

    def target():
        """T.

        Returns
        -------
        float
            Mine.
        """

    docwrap(target, format='numpy', inheritreturns=many, returnmap={0: 1})
    assert target.__doc__.endswith('float\n    First.\nfloat\n    Mine.')


def test_raisemap_and_ignoreraises_through_the_decorator():
    def target():
        """T."""

    docwrap(
        target, format='numpy', inheritraises=source, ignoreraises='ValueError'
    )
    assert 'If bad.' not in target.__doc__


def test_a_source_may_be_bound_to_one_item_at_the_top_level():
    def other(foo, bar=1):
        """O.

        Parameters
        ----------
        foo : float
            The foo from other.
        """

    def target(foo, bar=1):
        """T."""

    docwrap(
        target,
        format='numpy',
        inheritparams=(source, other, (source, 'foo')),
    )
    assert 'The foo parameter.' in target.__doc__
    assert 'The foo from other.' not in target.__doc__


def test_a_lone_binding_is_not_read_as_two_sources():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inheritparams=(source, 'foo'))
    assert 'The foo parameter.' in target.__doc__
    assert 'The bar parameter' not in target.__doc__


def test_a_boolean_is_never_an_item_key():
    from docshare._decorator import _as_source_specs, _is_item_key

    assert _is_item_key(True) is False
    assert _as_source_specs((source, True)) == (source, True)


def test_drop_accepts_an_iterable_of_positions():
    def many():
        """M.

        Returns
        -------
        float
            First.
        float
            Second.
        float
            Third.
        """

    def target():
        """T."""

    docwrap(target, format='numpy', inheritreturns=many, ignorereturns=[0, 2])
    assert 'Second.' in target.__doc__
    assert 'First.' not in target.__doc__
    assert 'Third.' not in target.__doc__


def test_passing_none_for_a_drop_is_the_same_as_omitting_it():
    def target(foo, bar=1):
        """T."""

    docwrap(target, format='numpy', inheritparams=source, dropparams=None)
    assert 'The foo parameter.' in target.__doc__
    assert 'The bar parameter' in target.__doc__


def test_a_position_bound_to_parameters_is_rejected_by_the_decorator():
    def target(foo, bar=1):
        """T."""

    with pytest.raises(DocMappingError, match='identified by name'):
        docwrap(target, format='numpy', inheritparams=(source, 0))


def test_a_dead_binding_no_longer_passes_silently():
    # Before, this inherited nothing at all and said nothing about it.
    original = 'T.'

    def target(foo, bar=1):
        pass

    target.__doc__ = original
    with pytest.raises(DocMappingError):
        docwrap(target, format='numpy', inheritparams=(source, 0))
    assert target.__doc__ == original


def test_inheritall_does_not_pick_up_untitled_prose():
    def base(x):
        """B.

        Args:
            x (int): The x.

        Trailing prose that is not a section.
        """

    @docwrap(format='google', inheritall=base, inheritother=True)
    def target(x):
        """T."""

    assert 'The x.' in target.__doc__
    assert 'Trailing prose' not in target.__doc__


# Sources are resolved before the engine sees them ###########################


def _every_source(operations):
    """Yield every source entry of every operation."""
    for operation in operations:
        for entry in operation.sources:
            yield entry[0] if isinstance(entry, tuple) else entry


def test_the_engine_is_handed_documents_rather_than_objects():
    # Deciding how a source is read belongs to the decorator; the engine
    # only composes. Every source is therefore parsed before any operation
    # is built.
    options = {
        'format': 'numpy',
        'inheritparams': source,
        'inheritreturns': (source, described),
        'inheritraises': ((source, 'ValueError'),),
        'inheritsummary': described,
        'inheritother': [(source, 'Efferents')],
    }
    operations = _operations(options, _Sources())
    entries = list(_every_source(operations))
    assert entries
    assert all(isinstance(entry, Document) for entry in entries)


def test_inheritall_also_hands_over_documents():
    operations = _operations(
        {'inheritall': source, 'inheritother': True}, _Sources()
    )
    entries = list(_every_source(operations))
    assert entries
    assert all(isinstance(entry, Document) for entry in entries)


def test_a_source_named_by_several_arguments_is_parsed_once(monkeypatch):
    calls = []
    original = _decorator.source_document

    def counted(obj):
        calls.append(obj)
        return original(obj)

    monkeypatch.setattr(_decorator, 'source_document', counted)
    _operations(
        {
            'inheritparams': source,
            'inheritreturns': source,
            'inheritraises': source,
            'inheritnotes': source,
        },
        _Sources(),
    )
    assert calls == [source]


def test_a_document_source_is_passed_straight_through():
    parsed = docinfo(described, format='numpy')
    resolved = _Sources().resolve(parsed)
    assert resolved is parsed
