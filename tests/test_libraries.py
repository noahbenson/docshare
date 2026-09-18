# -*- coding: utf-8 -*-
"""Tests against the docstrings of real libraries.

`docshare` exists to share documentation with code that was written without
any knowledge of it, so the docstrings it has to cope with are not the ones
in its own test corpus. These tests read two libraries that document
themselves carefully and in opposite styles --- NumPy for NumPy style, and
Google's own absl-py for Google style --- and check that every documented
object parses, that parsing and rendering preserves it, and that a thin
wrapper can inherit from it.

Nothing here requires either library to be decorated, or even to know that
`docshare` exists: a source is anything with a docstring.

The libraries are installed by the `test` extra. The tests skip cleanly when
they are absent, so the package can still be tested without them.
"""

import warnings

import pytest

from docshare import (
    DocShareError,
    clear_docinfo,
    docparse,
    docwrap,
    section_kind,
)
from docshare._render import render_document

numpy = pytest.importorskip('numpy', reason='needs the test extra')
absl_app = pytest.importorskip('absl.app', reason='needs the test extra')
absl_flags = pytest.importorskip('absl.flags', reason='needs the test extra')
absl_logging = pytest.importorskip(
    'absl.logging', reason='needs the test extra'
)


@pytest.fixture(autouse=True)
def _empty_cache():
    clear_docinfo()
    yield
    clear_docinfo()


def documented(module):
    """Yield the documented public objects of a module.

    Accessing a deprecated name raises rather than warns, because the test
    configuration turns warnings into errors, so anything a library has
    deprecated drops out here instead of pinning the tests to a version.
    """
    for name in sorted(dir(module)):
        if name.startswith('_'):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error')
                obj = getattr(module, name)
        except Exception:
            continue
        doc = getattr(obj, '__doc__', None)
        if isinstance(doc, str) and doc.strip():
            yield (name, obj)


def semantics(doc):
    """Reduce a document to what rendering must preserve.

    An item described without a type is written with the type its section
    requires, since the NumPy standard demands one, so a document that has
    been rendered may carry a type where the original had none. That repair
    is deliberate, and is normalized away here so that it is not mistaken
    for a change of meaning. Anything else counts.
    """
    reduced = []
    for section in doc.sections:
        kind = section_kind(section.kind) if section.kind else None
        supplied = kind.placeholder if kind else None
        items = tuple(
            item.evolve(type=None)
            if supplied and not item.names and item.type == supplied
            else item
            for item in section.items
        )
        reduced.append((section.kind, items, section.text))
    return (doc.summary, tuple(reduced))


MODULES = [
    ('numpy', numpy),
    ('absl.app', absl_app),
    ('absl.flags', absl_flags),
    ('absl.logging', absl_logging),
]


# Whole-library surveys ######################################################


@pytest.mark.parametrize('label,module', MODULES, ids=[m[0] for m in MODULES])
def test_every_documented_object_parses(label, module):
    failures = []
    for name, obj in documented(module):
        try:
            docparse(obj)
        except DocShareError as error:
            failures.append(f'{label}.{name}: {error}')
    assert not failures, '\n'.join(failures[:10])


@pytest.mark.parametrize('label,module', MODULES, ids=[m[0] for m in MODULES])
def test_every_documented_object_survives_a_round_trip(label, module):
    failures = []
    for name, obj in documented(module):
        doc = docparse(obj)
        if doc.format is None:
            continue
        try:
            again = docparse(render_document(doc))
        except DocShareError as error:
            failures.append(f'{label}.{name}: re-parse failed: {error}')
            continue
        if semantics(again) != semantics(doc):
            failures.append(f'{label}.{name}: changed meaning')
    assert not failures, '\n'.join(failures[:10])


@pytest.mark.parametrize('label,module', MODULES, ids=[m[0] for m in MODULES])
def test_a_survey_actually_examined_something(label, module):
    # Guards the surveys above against silently examining nothing.
    assert sum(1 for _ in documented(module)) >= 5


def test_the_numpy_survey_is_substantial():
    assert sum(1 for _ in documented(numpy)) > 100


# NumPy style ################################################################


def test_a_wrapper_inherits_numpy_parameter_documentation():
    @docwrap(format='numpy', inheritparams=numpy.sum, extraparam='axis')
    def total(a, axis=None):
        """Sum an array, but ours.

        Returns
        -------
        numpy.ndarray
            The sum.
        """

    assert 'a : array_like' in total.__doc__
    assert 'Elements to sum.' in total.__doc__
    assert 'axis :' in total.__doc__
    assert total.__doc__.startswith('Sum an array, but ours.')


def test_a_wrapper_keeps_its_own_documentation():
    @docwrap(format='numpy', inheritparams=numpy.sum)
    def total(a):
        """Ours.

        Parameters
        ----------
        a : list
            Our own description of a.
        """

    assert 'Our own description of a.' in total.__doc__
    assert 'Elements to sum.' not in total.__doc__


def test_only_parameters_the_wrapper_has_are_inherited():
    @docwrap(format='numpy', inheritparams=numpy.linspace)
    def line(start, stop):
        """Ours."""

    declared = [
        item.names for item in docparse(line).section('parameters').items
    ]
    # numpy.linspace also documents num, endpoint, retstep, dtype and axis,
    # none of which this wrapper accepts. They may still be *mentioned* in
    # an inherited description, which is why the check is on declarations.
    assert declared == [('start',), ('stop',)]


def test_a_renamed_group_inherits_whole_and_stays_grouped():
    # numpy.clip documents a_min and a_max in one grouped declaration, so
    # renaming both keeps the group intact rather than splitting it.
    @docwrap(
        format='numpy',
        inheritparams=numpy.clip,
        parammap={'lower': 'a_min', 'upper': 'a_max'},
    )
    def bound(a, lower=None, upper=None):
        """Ours."""

    declared = [
        item.names for item in docparse(bound).section('parameters').items
    ]
    assert declared == [('a',), ('lower', 'upper')]
    assert 'lower, upper :' in bound.__doc__


def test_renaming_only_part_of_a_real_group_is_refused():
    from docshare import DocInheritanceError

    with pytest.raises(DocInheritanceError, match='whole or not at all'):

        @docwrap(
            format='numpy',
            inheritparams=numpy.clip,
            parammap={'lower': 'a_min'},
        )
        def bound(a, lower=None):
            """Ours."""


def test_a_section_can_be_inherited_whole():
    @docwrap(format='numpy', inheritnotes=numpy.mean)
    def average(a):
        """Ours."""

    assert average.__doc__ != 'Ours.'
    assert docparse(average).section('notes') is not None


def test_several_numpy_sources_resolve_right_to_left():
    @docwrap(format='numpy', inheritparams=(numpy.sum, numpy.mean))
    def statistic(a):
        """Ours."""

    assert 'a : array_like' in statistic.__doc__


# Google style ###############################################################


def test_a_wrapper_inherits_google_parameter_documentation():
    @docwrap(format='google', inheritparams=absl_logging.log_every_n)
    def every(level, msg, n):
        """Ours."""

    declared = [
        item.names for item in docparse(every).section('parameters').items
    ]
    assert ('level',) in declared
    assert ('msg',) in declared
    assert 'Args:' in every.__doc__


def test_absl_flag_attributes_parse():
    # This class ends its Attributes section and then explains itself in
    # unindented prose, which used to be read as further attributes.
    doc = docparse(absl_flags.Flag)
    attributes = doc.section('attributes')
    assert attributes is not None
    names = [item.names[0] for item in attributes.items]
    assert 'name' in names
    assert 'default' in names
    assert all(' ' not in name for name in names)


def test_absl_flag_trailing_prose_is_preserved():
    doc = docparse(absl_flags.Flag)
    untitled = [s for s in doc.sections if s.opaque and not s.name]
    assert untitled
    assert any('parse' in line for line in untitled[0].text)


def test_a_wrapper_inherits_google_attributes():
    @docwrap(
        format='google',
        inheritattributes=absl_flags.Flag,
        ignoreattributes='validators',
    )
    class Wrapper:
        """Ours."""

    assert 'name' in Wrapper.__doc__
    assert 'validators' not in Wrapper.__doc__


# Across the two styles ######################################################


def test_a_google_wrapper_inherits_from_a_numpy_source():
    @docwrap(inheritparams=numpy.sum, extraparam='axis')
    def total(a, axis=None):
        """Ours.

        Args:
            axis (int): Our own axis.
        """

    body = total.__doc__
    assert 'Args:' in body
    assert 'Parameters\n----------' not in body
    assert 'a (array_like):' in body
    assert 'Our own axis.' in body


def test_a_numpy_wrapper_inherits_from_a_google_source():
    @docwrap(inheritparams=absl_logging.log_every_n)
    def every(level, msg, n):
        """Ours.

        Parameters
        ----------
        n : int
            Our own n.
        """

    body = every.__doc__
    assert 'Parameters\n----------' in body
    assert 'Args:' not in body
    assert 'Our own n.' in body


def test_a_numpy_source_can_be_rendered_as_google():
    doc = docparse(numpy.sum)
    out = render_document(doc, format='google')
    assert 'Args:' in out
    assert 'a (array_like):' in out
    assert docparse(out).format == 'google'


# The summary and the description ############################################


def test_a_ufunc_signature_line_is_not_read_as_a_summary():
    doc = docparse(numpy.log)
    assert doc.meta['signature'].startswith('log(')
    assert doc.summary == 'Natural logarithm, element-wise.'


def test_a_ufunc_signature_line_is_written_back_out():
    doc = docparse(numpy.log)
    assert render_document(doc).startswith(doc.meta['signature'])


def test_inheritall_from_a_ufunc_takes_its_header_text():
    @docwrap(inheritall=numpy.log, render='google')
    def google_log(x, /, out=None, *, where=True, **kwargs):
        return numpy.log(x, out=out, where=where, **kwargs)

    body = google_log.__doc__
    assert body.startswith('Natural logarithm, element-wise.')
    assert 'The natural logarithm `log` is the inverse' in body
    assert 'Args:' in body
    # The signature belongs to numpy.log alone and is never handed on.
    assert "casting='same_kind'" not in body


def test_a_wrapper_keeps_its_own_summary_over_an_inherited_one():
    @docwrap(inheritall=numpy.log, render='numpy')
    def our_log(x, /, out=None, *, where=True, **kwargs):
        """Take a logarithm, our way."""
        return numpy.log(x, out=out, where=where, **kwargs)

    body = our_log.__doc__
    assert body.startswith('Take a logarithm, our way.')
    assert 'Natural logarithm, element-wise.' not in body
    assert 'Parameters\n----------' in body
