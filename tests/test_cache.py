# -*- coding: utf-8 -*-
"""Tests for docparse, docinfo, and the documentation cache."""

import gc
import weakref

import pytest

from docshare import (
    DocFormatError,
    Document,
    clear_docinfo,
    docinfo,
    docparse,
)
from docshare._cache import _CACHE, cache_key, documentation, set_docinfo

PARAMS = 'S.\n\nParameters\n----------\nx : int\n    The x.\n'
OTHER = 'S.\n\nParameters\n----------\ny : str\n    The y.\n'


@pytest.fixture(autouse=True)
def _empty_cache():
    clear_docinfo()
    yield
    clear_docinfo()


def make_function(doc=PARAMS):
    def f():
        pass

    f.__doc__ = doc
    return f


# docparse ###################################################################


def test_docparse_reads_the_objects_documentation():
    doc = docparse(make_function())
    assert doc.section('parameters').items[0].names == ('x',)


def test_docparse_of_an_undocumented_object_is_empty():
    def f():
        pass

    assert docparse(f).empty


def test_docparse_of_a_string_parses_that_string():
    # A string is documentation, not an object that has documentation;
    # otherwise this would parse the docstring of the str type itself.
    assert docparse(PARAMS).section('parameters').items[0].names == ('x',)


def test_docparse_never_populates_the_cache():
    f = make_function()
    docparse(f)
    assert len(_CACHE) == 0


def test_docparse_never_consults_the_cache():
    f = make_function()
    set_docinfo(f, Document(summary='Recorded.'))
    assert docparse(f).summary == 'S.'


def test_docparse_reflects_a_reassigned_docstring():
    f = make_function()
    assert docparse(f).section('parameters').items[0].names == ('x',)
    f.__doc__ = OTHER
    assert docparse(f).section('parameters').items[0].names == ('y',)


def test_docparse_honors_an_explicit_format():
    f = make_function()
    assert docparse(f, format='numpy').format == 'numpy'


def test_docparse_rejects_a_mismatched_format():
    f = make_function()
    with pytest.raises(DocFormatError):
        docparse(f, format='google')


# docinfo ####################################################################


def test_docinfo_parses_when_nothing_is_recorded():
    f = make_function()
    assert docinfo(f).section('parameters').items[0].names == ('x',)


def test_docinfo_records_what_it_parsed():
    f = make_function()
    first = docinfo(f)
    assert docinfo(f) is first


def test_docinfo_returns_what_composition_recorded():
    # Composition records the assembled document, which may document more
    # than the object's own docstring ever did.
    f = make_function()
    composed = Document(summary='Composed.')
    set_docinfo(f, composed, text=f.__doc__)
    assert docinfo(f) is composed


def test_docinfo_of_an_undocumented_object_is_empty():
    def f():
        pass

    assert docinfo(f).empty


def test_docinfo_of_a_string_is_not_cached():
    assert docinfo(PARAMS).section('parameters').items[0].names == ('x',)
    assert len(_CACHE) == 0


# Format handling ############################################################


def test_docinfo_format_applies_only_when_parsing_happens():
    f = make_function()
    first = docinfo(f, format='numpy')
    # The recorded document is returned whatever the format says, because
    # the representation does not depend on the format it was written in.
    assert docinfo(f, format='google') is first


def test_docinfo_format_is_used_when_it_must_parse():
    f = make_function()
    with pytest.raises(DocFormatError):
        docinfo(f, format='google')


# Fingerprinting #############################################################


def test_a_reassigned_docstring_invalidates_the_record():
    f = make_function()
    first = docinfo(f)
    f.__doc__ = OTHER
    second = docinfo(f)
    assert second is not first
    assert second.section('parameters').items[0].names == ('y',)


def test_a_docstring_restored_to_its_old_text_reparses_equal():
    f = make_function()
    first = docinfo(f)
    f.__doc__ = OTHER
    docinfo(f)
    f.__doc__ = PARAMS
    assert docinfo(f) == first


def test_clearing_a_docstring_yields_an_empty_document():
    f = make_function()
    docinfo(f)
    f.__doc__ = None
    assert docinfo(f).empty


# Object types ###############################################################


class Example:
    """Example class.

    Attributes
    ----------
    value : int
        The value.
    """

    def method(self):
        """A method.

        Parameters
        ----------
        a : int
            The a.
        """

    @staticmethod
    def static():
        """A static method.

        Parameters
        ----------
        b : int
            The b.
        """

    @classmethod
    def klass(cls):
        """A class method.

        Parameters
        ----------
        c : int
            The c.
        """

    @property
    def prop(self):
        """A property.

        Returns
        -------
        int
            The value.
        """


def test_a_class_is_cached():
    assert docinfo(Example).section('attributes').items[0].names == ('value',)
    assert docinfo(Example) is docinfo(Example)


def test_a_plain_function_is_cached():
    f = make_function()
    assert docinfo(f) is docinfo(f)


def test_a_staticmethod_object_is_cached():
    obj = Example.__dict__['static']
    assert docinfo(obj).section('parameters').items[0].names == ('b',)
    assert docinfo(obj) is docinfo(obj)


def test_a_classmethod_object_is_cached():
    obj = Example.__dict__['klass']
    assert docinfo(obj).section('parameters').items[0].names == ('c',)
    assert docinfo(obj) is docinfo(obj)


def test_a_property_object_is_cached():
    obj = Example.__dict__['prop']
    assert docinfo(obj).section('returns').items[0].type == 'int'
    assert docinfo(obj) is docinfo(obj)


def test_a_bound_method_is_cached_across_separate_accesses():
    # A new bound method is created on each access, so caching one directly
    # would never hit; the cache keys on the underlying function.
    instance = Example()
    assert instance.method is not instance.method
    assert docinfo(instance.method) is docinfo(instance.method)


def test_a_bound_method_and_its_function_share_a_record():
    instance = Example()
    assert docinfo(instance.method) is docinfo(Example.method)


def test_an_instance_uses_its_class_documentation():
    assert docinfo(Example()).section('attributes') is not None


# Cache keys #################################################################


@pytest.mark.parametrize(
    'obj',
    [
        Example,
        Example.method,
        Example.__dict__['static'],
        Example.__dict__['klass'],
        Example.__dict__['prop'],
    ],
)
def test_supported_objects_all_have_a_cache_key(obj):
    assert cache_key(obj) is not None


def test_a_descriptor_keys_on_its_underlying_function():
    assert (
        cache_key(Example.__dict__['static'])
        is Example.__dict__['static'].__func__
    )
    assert cache_key(Example.__dict__['prop']) is Example.__dict__['prop'].fget


def test_a_bound_method_keys_on_its_function():
    instance = Example()
    assert cache_key(instance.method) is Example.method


def test_an_object_that_cannot_be_referenced_has_no_key():
    assert cache_key(5) is None
    assert cache_key((1, 2)) is None


def test_a_string_has_no_key():
    assert cache_key('some docs') is None


def test_an_unreferenceable_object_still_parses():
    # Caching is an optimization; correctness does not depend on it.
    assert docinfo(5).summary is not None
    assert len(_CACHE) == 0


def test_a_write_only_property_has_no_underlying_getter():
    prop = property(None, lambda self, value: None, doc='Write only.')
    assert cache_key(prop) is None
    assert docinfo(prop).summary == 'Write only.'


# Weak references ############################################################


def test_the_cache_does_not_keep_an_object_alive():
    f = make_function()
    docinfo(f)
    assert len(_CACHE) == 1
    reference = weakref.ref(f)
    del f
    gc.collect()
    assert reference() is None
    assert len(_CACHE) == 0


def test_the_cache_does_not_modify_the_documented_object():
    f = make_function()
    before = set(vars(f))
    docinfo(f)
    assert set(vars(f)) == before
    assert f.__doc__ == PARAMS


# set_docinfo and clear_docinfo ##############################################


def test_set_docinfo_reports_failure_for_an_unkeyable_object():
    assert set_docinfo(5, Document()) is False


def test_set_docinfo_reports_success_for_a_function():
    assert set_docinfo(make_function(), Document()) is True


def test_set_docinfo_defaults_to_the_current_docstring():
    f = make_function()
    recorded = Document(summary='Composed.')
    set_docinfo(f, recorded)
    assert docinfo(f) is recorded


def test_clear_docinfo_forgets_one_object():
    f = make_function()
    g = make_function()
    first = docinfo(f)
    docinfo(g)
    clear_docinfo(f)
    assert docinfo(f) is not first
    assert len(_CACHE) == 2


def test_clear_docinfo_forgets_everything():
    docinfo(make_function())
    docinfo(Example)
    clear_docinfo()
    assert len(_CACHE) == 0


def test_clear_docinfo_of_an_unkeyable_object_is_harmless():
    clear_docinfo(5)


def test_clear_docinfo_of_an_unrecorded_object_is_harmless():
    clear_docinfo(make_function())


# documentation() ############################################################


def test_documentation_of_a_string_is_itself():
    assert documentation('abc') == 'abc'


def test_documentation_of_an_undocumented_object():
    def f():
        pass

    assert documentation(f) is None
