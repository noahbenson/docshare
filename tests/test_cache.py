# -*- coding: utf-8 -*-
"""Tests for docparse, docinfo, and the documentation cache."""

import gc
import weakref

import pytest

from docshare import (
    DocCache,
    DocFormatError,
    Document,
    clear_docinfo,
    doccache,
    docinfo,
    docparse,
    docwrap,
)
from docshare._cache import DEFAULT_MAXSIZE, documentation, set_docinfo

PARAMS = 'S.\n\nParameters\n----------\nx : int\n    The x.\n'
OTHER = 'S.\n\nParameters\n----------\ny : str\n    The y.\n'


@pytest.fixture(autouse=True)
def _empty_cache():
    size = doccache.maxsize
    clear_docinfo()
    yield
    clear_docinfo()
    doccache.maxsize = size


def make_function(doc=PARAMS):
    def f():
        pass

    f.__doc__ = doc
    return f


# docparse ###################################################################


def test_docparse_reads_the_objects_documentation():
    assert docparse(make_function()).section('parameters').items[0].names == (
        'x',
    )


def test_docparse_of_an_undocumented_object_is_empty():
    def f():
        pass

    assert docparse(f).empty


def test_docparse_of_a_string_parses_that_string():
    # A string is documentation, not an object that has documentation;
    # otherwise this would parse the docstring of the str type itself.
    assert docparse(PARAMS).section('parameters').items[0].names == ('x',)


def test_docparse_never_populates_the_cache():
    docparse(make_function())
    assert len(doccache) == 0


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
    assert docparse(make_function(), format='numpy').format == 'numpy'


def test_docparse_rejects_a_mismatched_format():
    with pytest.raises(DocFormatError):
        docparse(make_function(), format='google')


# docinfo ####################################################################


def test_docinfo_parses_when_nothing_is_recorded():
    assert docinfo(make_function()).section('parameters').items[0].names == (
        'x',
    )


def test_docinfo_records_what_it_parsed():
    f = make_function()
    assert docinfo(f) is docinfo(f)


def test_docinfo_returns_what_composition_recorded():
    f = make_function()
    composed = Document(summary='Composed.')
    set_docinfo(f, composed)
    assert docinfo(f) is composed


def test_docinfo_of_an_undocumented_object_is_empty():
    def f():
        pass

    assert docinfo(f).empty


def test_every_undocumented_object_shares_one_record():
    def f():
        pass

    def g():
        pass

    assert docinfo(f) is docinfo(g)


def test_a_string_is_cached_like_anything_else():
    assert docinfo(PARAMS) is docinfo(PARAMS)


# Keyed by the documentation, not by the object ##############################


def test_two_objects_documented_alike_share_one_record():
    # A parsed document depends on nothing but the text it came from.
    assert docinfo(make_function()) is docinfo(make_function())
    assert len(doccache) == 1


def test_two_objects_documented_differently_do_not():
    docinfo(make_function(PARAMS))
    docinfo(make_function(OTHER))
    assert len(doccache) == 2


def test_the_cache_is_keyed_by_the_format_and_the_docstring():
    docinfo(make_function())
    assert list(doccache) == [(None, PARAMS)]


def test_an_explicit_format_is_part_of_the_key():
    docinfo(make_function(), format='numpy')
    assert list(doccache) == [('numpy', PARAMS)]


def test_a_reassigned_docstring_misses_and_is_reparsed():
    f = make_function()
    first = docinfo(f)
    f.__doc__ = OTHER
    second = docinfo(f)
    assert second is not first
    assert second.section('parameters').items[0].names == ('y',)


def test_a_docstring_restored_to_its_old_text_hits_again():
    f = make_function()
    first = docinfo(f)
    f.__doc__ = OTHER
    docinfo(f)
    f.__doc__ = PARAMS
    assert docinfo(f) is first


def test_the_cache_never_refers_to_the_documented_object():
    f = make_function()
    docinfo(f)
    reference = weakref.ref(f)
    del f
    gc.collect()
    assert reference() is None
    assert len(doccache) == 1


def test_the_cache_does_not_modify_the_documented_object():
    f = make_function()
    before = set(vars(f))
    docinfo(f)
    assert set(vars(f)) == before
    assert f.__doc__ == PARAMS


# Format handling ############################################################


# One text can be read two ways, so the format is part of the key. A NumPy
# declaration with an empty type has the shape of a Google section header,
# which makes this docstring a Parameters section with a `notes` parameter in
# one format and a Notes section in the other.
AMBIGUOUS = 'S.\n\nParameters\n----------\nnotes :\n    Some notes.\n'


def test_a_document_parsed_as_one_format_does_not_answer_for_the_other():
    as_numpy = docinfo(AMBIGUOUS, format='numpy')
    as_google = docinfo(AMBIGUOUS, format='google')
    assert as_numpy is not as_google
    assert [s.kind for s in as_numpy.sections] == ['parameters']
    assert [s.kind for s in as_google.sections] == ['notes']


def test_the_order_of_the_requests_does_not_matter():
    first = docinfo(AMBIGUOUS, format='google')
    clear_docinfo()
    docinfo(AMBIGUOUS, format='numpy')
    again = docinfo(AMBIGUOUS, format='google')
    assert [s.kind for s in again.sections] == [s.kind for s in first.sections]


def test_each_format_gets_its_own_entry():
    docinfo(AMBIGUOUS, format='numpy')
    docinfo(AMBIGUOUS, format='google')
    docinfo(AMBIGUOUS, format='numpy')
    assert len(doccache) == 2


def test_a_repeated_request_for_one_format_still_hits():
    f = make_function()
    assert docinfo(f, format='numpy') is docinfo(f, format='numpy')


def test_docinfo_format_is_used_when_it_must_parse():
    with pytest.raises(DocFormatError):
        docinfo(make_function(), format='google')


def test_a_failed_parse_records_nothing():
    with pytest.raises(DocFormatError):
        docinfo(make_function(), format='google')
    assert len(doccache) == 0


# Every object type, including the ones that resisted weak reference #########


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


@pytest.mark.parametrize(
    'name',
    ['method', 'static', 'klass', 'prop'],
)
def test_every_descriptor_is_cached(name):
    obj = Example.__dict__[name]
    assert docinfo(obj) is docinfo(obj)


def test_a_class_is_cached():
    assert docinfo(Example) is docinfo(Example)


def test_a_bound_method_is_cached_across_separate_accesses():
    instance = Example()
    assert instance.method is not instance.method
    assert docinfo(instance.method) is docinfo(instance.method)


def test_a_write_only_property_is_cached():
    # It has no getter to key on, and used not to be cached at all.
    prop = property(None, lambda self, value: None, doc=PARAMS)
    assert docinfo(prop) is docinfo(prop)
    assert docinfo(prop).section('parameters') is not None


def test_an_object_that_cannot_be_weakly_referenced_is_cached():
    class Slotted:
        __slots__ = ()
        __doc__ = PARAMS

    obj = Slotted()
    with pytest.raises(TypeError):
        weakref.ref(obj)
    assert docinfo(obj) is docinfo(obj)


def test_a_descriptor_with_its_own_docstring_does_not_collide():
    # A property built over a documented function, with documentation of its
    # own, used to share that function's cache entry.
    def getter(self):
        """The getter's own documentation."""

    prop = property(getter, doc=PARAMS)
    assert docinfo(prop) is not docinfo(getter)
    assert docinfo(prop).section('parameters') is not None
    assert docinfo(getter).section('parameters') is None


# Bound size #################################################################


def test_the_cache_is_bounded():
    doccache.maxsize = 3
    for index in range(10):
        docinfo(f'Document number {index}.')
    assert len(doccache) == 3


def test_the_oldest_entry_is_discarded_first():
    doccache.maxsize = 2
    docinfo('First.')
    docinfo('Second.')
    docinfo('Third.')
    assert (None, 'First.') not in doccache
    assert (None, 'Third.') in doccache


def test_reading_an_entry_makes_it_recent():
    doccache.maxsize = 2
    docinfo('First.')
    docinfo('Second.')
    docinfo('First.')  # touches it
    docinfo('Third.')
    assert (None, 'First.') in doccache
    assert (None, 'Second.') not in doccache


def test_lowering_the_bound_discards_at_once():
    for index in range(10):
        docinfo(f'Document number {index}.')
    doccache.maxsize = 4
    assert len(doccache) == 4


def test_a_zero_bound_disables_caching():
    doccache.maxsize = 0
    f = make_function()
    assert docinfo(f) is not docinfo(f)
    assert len(doccache) == 0


def test_a_negative_bound_is_treated_as_zero():
    doccache.maxsize = -5
    assert doccache.maxsize == 0


def test_the_default_bound_is_generous():
    assert DEFAULT_MAXSIZE >= 1024
    assert DocCache().maxsize == DEFAULT_MAXSIZE


# The cache as a mapping #####################################################


def test_the_cache_is_a_mapping():
    docinfo(make_function())
    assert len(doccache) == 1
    assert (None, PARAMS) in doccache
    assert isinstance(doccache[(None, PARAMS)], Document)
    assert next(iter(doccache.values())) is doccache[(None, PARAMS)]


def test_an_entry_can_be_removed():
    docinfo(make_function())
    del doccache[(None, PARAMS)]
    assert len(doccache) == 0


def test_an_entry_can_be_supplied_by_hand():
    doccache[(None, 'Invented.')] = Document(summary='Invented.')
    assert docinfo('Invented.').summary == 'Invented.'


def test_the_cache_reports_its_size_and_bound():
    assert 'maxsize' in repr(doccache)
    assert 'entries' in repr(doccache)


def test_an_independent_cache_can_be_made():
    other = DocCache(maxsize=1)
    other[(None, 'a')] = Document(summary='A.')
    other[(None, 'b')] = Document(summary='B.')
    assert len(other) == 1
    assert len(doccache) == 0


# set_docinfo and clear_docinfo ##############################################


def test_set_docinfo_defaults_to_the_current_docstring():
    f = make_function()
    recorded = Document(summary='Composed.')
    set_docinfo(f, recorded)
    assert docinfo(f) is recorded


def test_set_docinfo_accepts_an_explicit_text():
    recorded = Document(summary='Composed.')
    set_docinfo(None, recorded, text='Some text.')
    assert docinfo('Some text.') is recorded


def test_set_docinfo_answers_for_the_format_it_was_written_in():
    recorded = Document(summary='Composed.', format='numpy')
    set_docinfo(None, recorded, text='Some text.', format='numpy')
    assert docinfo('Some text.') is recorded
    assert docinfo('Some text.', format='numpy') is recorded


def test_a_composed_record_answers_a_later_request_in_either_way():
    def base(x):
        """B.

        Parameters
        ----------
        x : int
            The x from base.
        """

    @docwrap(format='numpy', inheritparams=base)
    def wrapper(x):
        """W."""

    assert docinfo(wrapper) is docinfo(wrapper, format='numpy')


def test_clear_docinfo_forgets_every_format_of_one_object():
    f = make_function()
    docinfo(f)
    docinfo(f, format='numpy')
    assert len(doccache) == 2
    clear_docinfo(f)
    assert len(doccache) == 0


def test_clear_docinfo_forgets_one_object():
    f = make_function(PARAMS)
    g = make_function(OTHER)
    first = docinfo(f)
    docinfo(g)
    clear_docinfo(f)
    assert docinfo(f) is not first
    assert len(doccache) == 2


def test_clear_docinfo_forgets_everything():
    docinfo(make_function())
    docinfo(Example)
    clear_docinfo()
    assert len(doccache) == 0


def test_clear_docinfo_of_an_unrecorded_object_is_harmless():
    clear_docinfo(make_function())


# Composition records its result #############################################


def test_composition_records_the_composed_document():
    def base(x):
        """B.

        Parameters
        ----------
        x : int
            The x from base.
        """

    @docwrap(format='numpy', inheritparams=base)
    def wrapper(x):
        """W."""

    recorded = docinfo(wrapper)
    assert recorded.section('parameters').items[0].names == ('x',)
    assert doccache[(None, wrapper.__doc__)] is recorded


def test_a_composed_object_can_itself_be_inherited_from():
    def base(x):
        """B.

        Parameters
        ----------
        x : int
            The x from base.
        """

    @docwrap(format='numpy', inheritparams=base)
    def middle(x):
        """M."""

    @docwrap(format='numpy', inheritparams=middle)
    def leaf(x):
        """L."""

    assert 'The x from base.' in leaf.__doc__


def test_functools_wraps_shares_the_composed_record():
    import functools

    def base(x):
        """B.

        Parameters
        ----------
        x : int
            The x from base.
        """

    @docwrap(format='numpy', inheritparams=base)
    def target(x):
        """T."""

    @functools.wraps(target)
    def wrapper(x):
        return target(x)

    # The wrapper carries the same docstring, so it carries the same record.
    assert docinfo(wrapper) is docinfo(target)


# documentation() ############################################################


def test_documentation_of_a_string_is_itself():
    assert documentation('abc') == 'abc'


def test_documentation_of_an_undocumented_object():
    def f():
        pass

    assert documentation(f) is None


# A parsed Document as a source (see the guide on inheriting) ################


def test_source_document_passes_a_document_through():
    from docshare._cache import source_document

    doc = docparse(PARAMS)
    assert source_document(doc) is doc


def test_source_document_looks_an_object_up():
    from docshare._cache import source_document

    f = make_function()
    assert source_document(f) is docinfo(f)


def test_source_document_does_not_read_a_documents_own_class_docstring():
    # A Document is an object with a docstring of its own; taking that would
    # document the target with the description of the Document class.
    from docshare._cache import source_document

    doc = docparse(PARAMS)
    assert source_document(doc).section('parameters') is not None
    assert 'semantic representation' not in str(source_document(doc).summary)


# Cache keys are checked #####################################################


@pytest.mark.parametrize(
    'key',
    [
        'a bare docstring',
        42,
        ('numpy',),
        (None, 'a', 'b'),
        ['numpy', 'a'],
        None,
    ],
)
def test_a_malformed_key_is_rejected(key):
    # A dictionary would accept any of these and never read it back, leaving
    # the cache quietly wrong instead of obviously broken.
    with pytest.raises(TypeError):
        doccache[key] = Document()


def test_an_unsupported_format_in_a_key_is_rejected():
    with pytest.raises(ValueError, match='not a documentation format'):
        doccache[('rest', 'text')] = Document()


def test_a_non_string_docstring_in_a_key_is_rejected():
    with pytest.raises(TypeError, match='string or None'):
        doccache[(None, 42)] = Document()


@pytest.mark.parametrize(
    'key',
    [(None, 'text'), ('numpy', 'text'), ('google', 'text'), (None, None)],
)
def test_every_well_formed_key_is_accepted(key):
    doccache[key] = Document(summary='X.')
    assert key in doccache
    assert doccache[key].summary == 'X.'
    del doccache[key]


@pytest.mark.parametrize('operation', ['get', 'contains', 'delete'])
def test_reading_with_a_malformed_key_is_rejected_too(operation):
    # Otherwise a bad key would simply miss, which is how the mistake would
    # go unnoticed in the first place.
    with pytest.raises(TypeError):
        if operation == 'get':
            doccache['bare']
        elif operation == 'contains':
            'bare' in doccache  # noqa: B015 - the lookup is the point
        else:
            del doccache['bare']


def test_every_key_the_library_writes_is_well_formed():
    # Exercises the paths that write to the cache, then checks what landed.
    from docshare._cache import _check_key

    clear_docinfo()
    docinfo(make_function())
    docinfo(make_function(OTHER), format='numpy')
    docinfo('S.\n\nArgs:\n    x (int): X.\n', format='google')

    def base(x):
        """B.

        Parameters
        ----------
        x : int
            The x.
        """

    @docwrap(format='numpy', inheritparams=base)
    def wrapper(x):
        """W."""

    @docwrap
    def bare(x):
        """Bare."""

    assert len(doccache) >= 5
    for key in doccache:
        _check_key(key)
        assert isinstance(key, tuple) and len(key) == 2
