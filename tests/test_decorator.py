# -*- coding: utf-8 -*-
"""Tests for the docshare decorator."""

import functools
import pydoc

import pytest

from docshare import (
    DocFormatError,
    DocInheritanceError,
    DocShareError,
    DocSignatureError,
    clear_docinfo,
    docinfo,
    docshare,
)
from docshare._decorator import SECTION_ARGUMENTS


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
    @docshare(format='numpy')
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

    @docshare(format='numpy', inheritparams=quuxatize)
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
    @docshare
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

    assert docshare(f, format='numpy', inheritparams=source) is f
    assert 'The foo parameter.' in f.__doc__


def test_the_decorator_returns_the_same_object():
    def f(x):
        """F."""

    assert docshare(format='numpy')(f) is f


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
    docshare(f)
    assert f.__doc__ == original


def test_the_parsed_document_is_recorded_even_without_inheritance():
    def f(x):
        """F.

        Parameters
        ----------
        x : int
            The x.
        """

    docshare(f)
    assert docinfo(f) is docinfo(f)
    assert docinfo(f).section('parameters') is not None


def test_the_composed_document_is_recorded():
    def f(foo, bar=1):
        """F."""

    docshare(f, format='numpy', inheritparams=source)
    recorded = docinfo(f)
    assert [i.names for i in recorded.section('parameters').items] == [
        ('foo',),
        ('bar',),
    ]


def test_a_composed_object_can_itself_be_inherited_from():
    def middle(foo, bar=1):
        """M."""

    docshare(middle, format='numpy', inheritparams=source)

    def leaf(foo, bar=1):
        """L."""

    docshare(leaf, format='numpy', inheritparams=middle)
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

    docshare(target, format='numpy', inheritparams=upstream)
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

    @docshare(format='numpy', inheritparams=base_method)
    def method(self, x):
        pass

    @docshare(format='numpy', inheritparams=base_static)
    @staticmethod
    def static_above(p):
        pass

    @staticmethod
    @docshare(format='numpy', inheritparams=base_static)
    def static_below(p):
        pass

    @docshare(format='numpy', inheritparams=base_static)
    @classmethod
    def class_above(cls, p):
        pass

    @classmethod
    @docshare(format='numpy', inheritparams=base_static)
    def class_below(cls, p):
        pass

    @docshare(format='numpy', inheritreturns=base_property)
    @property
    def property_above(self):
        pass

    @property
    @docshare(format='numpy', inheritreturns=base_property)
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

    @docshare(format='numpy', inheritattributes=base)
    class Target:
        """T."""

    assert 'The value from base.' in Target.__doc__


def test_functools_wraps_carries_the_composed_documentation():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inheritparams=source)

    @functools.wraps(target)
    def wrapper(*args, **kwargs):
        return target(*args, **kwargs)

    assert wrapper.__doc__ == target.__doc__


# Section 57: the result is ordinary documentation ###########################


def test_help_shows_the_composed_documentation():
    def f(foo, bar=1):
        """F."""

    docshare(f, format='numpy', inheritparams=source)
    rendered = pydoc.render_doc(f)
    assert 'The foo parameter.' in rendered


def test_the_docstring_is_a_plain_string():
    def f(foo, bar=1):
        """F."""

    docshare(f, format='numpy', inheritparams=source)
    assert type(f.__doc__) is str


# Generalized and bulk interfaces ############################################


def test_the_generalized_inherit_argument():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inherit={'Parameters': source})
    assert 'The foo parameter.' in target.__doc__


def test_the_generalized_inherit_accepts_a_kind_name():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inherit={'parameters': source})
    assert 'The foo parameter.' in target.__doc__


def test_the_generalized_inherit_rejects_an_unknown_section():
    def target(foo, bar=1):
        """T."""

    with pytest.raises(DocShareError, match='inheritother'):
        docshare(target, format='numpy', inherit={'Efferents': source})


def test_naming_a_section_twice_is_an_error():
    def target(foo, bar=1):
        """T."""

    with pytest.raises(DocShareError, match='one place or the other'):
        docshare(
            target,
            format='numpy',
            inherit={'Parameters': source},
            inheritparams=source,
        )


def test_inheritall_takes_every_recognized_section():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inheritall=source)
    assert 'The foo parameter.' in target.__doc__
    assert 'The quux.' in target.__doc__
    assert 'If bad.' in target.__doc__
    assert 'A note from the source.' in target.__doc__


def test_inheritall_leaves_unrecognized_sections_alone():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inheritall=source)
    assert 'Efferents' not in target.__doc__


def test_inheritall_with_inheritother_takes_unrecognized_sections_too():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inheritall=source, inheritother=True)
    assert 'Downstream connections.' in target.__doc__


def test_inheritother_takes_a_named_section():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inheritother=[(source, 'Efferents')])
    assert 'Downstream connections.' in target.__doc__
    assert 'The foo parameter.' not in target.__doc__


def test_inheritother_rejects_a_bare_source():
    def target(foo, bar=1):
        """T."""

    with pytest.raises(DocShareError, match='section name'):
        docshare(target, format='numpy', inheritother=[source])


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
        'dropreturns',
        'returnmap',
        'dropraises',
        'raisemap',
        'dropattributes',
        'attributemap',
        'dropotherparams',
        'otherparammap',
        'dropkeywordargs',
        'keywordargmap',
    ],
)
def test_section_42_naming_is_consistent(name):
    assert name in SECTION_ARGUMENTS


@pytest.mark.parametrize('name', ['inheritseealso', 'inheritreferences'])
def test_prose_sections_offer_only_inheritance(name):
    assert name in SECTION_ARGUMENTS
    assert f'drop{name[len("inherit") :]}' not in SECTION_ARGUMENTS


def test_an_unknown_argument_is_rejected():
    def f(x):
        """F."""

    with pytest.raises(DocShareError, match='unexpected argument'):
        docshare(f, inheritnothing=source)


def test_an_unknown_argument_suggests_a_close_match():
    def f(x):
        """F."""

    with pytest.raises(DocShareError, match='inheritparams'):
        docshare(f, inheritparam=source)


def test_a_misspelled_argument_is_caught_before_any_work():
    original = 'F.'

    def f(x):
        pass

    f.__doc__ = original
    with pytest.raises(DocShareError):
        docshare(f, dropparam='x')
    assert f.__doc__ == original


# Validation at decoration time ##############################################


def test_signature_validation_runs_at_decoration_time():
    with pytest.raises(DocSignatureError, match="'scal'"):

        @docshare(format='numpy')
        def f(scale=1):
            """F.

            Parameters
            ----------
            scal : int
                Typo.
            """


def test_extraparam_is_accepted():
    @docshare(format='numpy', extraparam='null')
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

    @docshare(format='numpy', inheritparams=base, extraparam='null')
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

        @docshare(format='numpy', inheritparams=grouped)
        def f(x, y, z):
            """F.

            Parameters
            ----------
            x : float
                Only one.
            """


# Formats ####################################################################


def test_an_undocumented_target_requires_an_explicit_format():
    def f(foo, bar=1):
        pass

    with pytest.raises(DocFormatError, match='no format is known'):
        docshare(f, inheritparams=source)


def test_an_undocumented_target_composes_with_an_explicit_format():
    def f(foo, bar=1):
        pass

    docshare(f, format='numpy', inheritparams=source)
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

    docshare(f, inheritparams=google_source, extraparam='baz')
    assert 'foo (float): The foo from google.' in f.__doc__


def test_the_format_argument_does_not_convert_a_document():
    # format= says what the docstring is written in, per specification
    # section 4.1, and the output is written in that same format. It is not
    # a conversion request; see docs/deferred.md.
    def f(foo, bar=1):
        """F.

        Parameters
        ----------
        bar : float
            My own bar.
        """

    with pytest.raises(DocFormatError, match='required to be'):
        docshare(f, format='google', inheritparams=source)


def test_a_google_target_may_inherit_from_a_numpy_source():
    # The document model is format-independent, so the source's style is
    # irrelevant; the target is written in its own.
    def f(foo, bar=1):
        """F.

        Args:
            bar (float): My own bar.
        """

    docshare(f, inheritparams=source)
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

    docshare(f, inheritparams=google_source)
    assert 'Parameters\n----------' in f.__doc__
    assert 'foo : float' in f.__doc__


def test_an_unwritable_docstring_is_reported():
    class Slotted:
        __slots__ = ()

    with pytest.raises(DocShareError, match='not writable'):
        docshare(Slotted(), format='numpy', inheritparams=source)


# Per-section arguments through the decorator ################################


def test_dropparams_through_the_decorator():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inheritparams=source, dropparams='foo')
    assert 'The foo parameter.' not in target.__doc__
    assert 'The bar parameter' in target.__doc__


def test_dropparams_accepts_several_names():
    def target(foo, bar=1):
        """T.

        Notes
        -----
        Keeps the document from being empty.
        """

    docshare(
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

    docshare(
        target,
        format='numpy',
        inheritparams=source,
        parammap={'inp': 'foo'},
    )
    assert 'inp : float' in target.__doc__
    assert 'The foo parameter.' in target.__doc__


def test_dropreturns_through_the_decorator():
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

    docshare(target, format='numpy', inheritreturns=many, dropreturns=0)
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

    docshare(target, format='numpy', inheritreturns=many, returnmap={0: 1})
    assert target.__doc__.endswith('float\n    First.\nfloat\n    Mine.')


def test_raisemap_and_dropraises_through_the_decorator():
    def target():
        """T."""

    docshare(
        target, format='numpy', inheritraises=source, dropraises='ValueError'
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

    docshare(
        target,
        format='numpy',
        inheritparams=(source, other, (source, 'foo')),
    )
    assert 'The foo parameter.' in target.__doc__
    assert 'The foo from other.' not in target.__doc__


def test_a_lone_binding_is_not_read_as_two_sources():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inheritparams=(source, 'foo'))
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

    docshare(target, format='numpy', inheritreturns=many, dropreturns=[0, 2])
    assert 'Second.' in target.__doc__
    assert 'First.' not in target.__doc__
    assert 'Third.' not in target.__doc__


def test_passing_none_for_a_drop_is_the_same_as_omitting_it():
    def target(foo, bar=1):
        """T."""

    docshare(target, format='numpy', inheritparams=source, dropparams=None)
    assert 'The foo parameter.' in target.__doc__
    assert 'The bar parameter' in target.__doc__
