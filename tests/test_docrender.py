# -*- coding: utf-8 -*-
"""Tests for composing and rendering documentation without an object.

`doccompose` and `docrender` do the work of `docwrap` without an object to
install the result on. An object brings its signature, so the documentation is
validated and its parameters ordered as for `docwrap`; a docstring or a
`Document` has none, so validation is skipped and a parameter section is
driven by its sources instead.
"""

import pytest

import docshare
from docshare import (
    DocShareError,
    DocSignatureError,
    Document,
    doccompose,
    docparse,
    docrender,
    docwrap,
)

TARGET_TEXT = """Returns the log of the quux.

    Parameters
    ----------
    base : float, optional
        The base of the log.
    """


def source(foo, bar=1):
    """Return the quux of two arguments.

    Parameters
    ----------
    foo : float
        The foo parameter.
    bar : float, optional
        The bar parameter.
    """
    return (foo * bar) ** (foo + bar)


def logquuxatize(foo, bar=1, base=None):
    """Return the log of the quux."""


def test_a_docstring_renders_on_its_own():
    text = docrender(TARGET_TEXT, format='numpy')
    assert text.startswith('Returns the log of the quux.')
    assert 'base : float, optional' in text
    assert '    The base of the log.' in text


def test_a_docstring_inherits_from_a_source():
    text = docrender(TARGET_TEXT, format='numpy', inheritparams=source)
    # The target's own parameter is kept, and the source's are added.
    assert 'base : float, optional' in text
    assert 'foo : float' in text
    assert 'bar : float, optional' in text


def test_a_source_parameter_the_text_lacks_is_inherited():
    # With no signature to say what exists, a parameter section is driven by
    # its sources, so the whole of the source's section is taken.
    text = docrender('Just a summary.', format='numpy', inheritparams=source)
    assert 'foo : float' in text
    assert 'bar : float, optional' in text


def test_rendering_converts_between_formats():
    text = docrender(
        TARGET_TEXT, format='numpy', render='google', inheritparams=source
    )
    assert 'Args:' in text
    assert 'Parameters\n----------' not in text


def test_rendering_is_not_an_identity():
    # Nothing is inherited, but the text is still rewritten.
    messy = 'Summary.\n\n\n\nParameters\n----------\nx : int\n    The x.\n'
    assert docrender(messy) != messy
    assert docrender(messy, format='numpy').startswith(
        'Summary.\n\nParameters'
    )


def test_an_object_brings_its_signature():
    # `logquuxatize` has no `base` in its signature, and the source does not
    # document it, so it is absent -- unlike the text-driven case.
    text = docrender(logquuxatize, format='numpy', inheritparams=source)
    assert 'foo : float' in text
    assert 'bar : float, optional' in text
    assert 'base' not in text


def test_an_object_is_validated_against_its_signature():
    def bad(x):
        """Bad.

        Parameters
        ----------
        y : int
            The y.
        """

    with pytest.raises(DocSignatureError):
        docrender(bad, format='numpy')


def test_a_document_may_be_composed_directly():
    parsed = docparse(TARGET_TEXT, format='numpy')
    assert docrender(parsed, inheritparams=source) == docrender(
        TARGET_TEXT, format='numpy', inheritparams=source
    )


def test_doccompose_returns_the_composed_document():
    doc = doccompose(TARGET_TEXT, format='numpy', inheritparams=source)
    assert isinstance(doc, Document)
    names = [item.names for item in doc.section('parameters').items]
    assert names == [('base',), ('foo',), ('bar',)]


def test_doccompose_keeps_the_parsed_format():
    # `format` is what the text is written in, not what it would be rendered
    # as; `doccompose` changes nothing about it.
    doc = doccompose(TARGET_TEXT, format='numpy', render='google')
    assert doc.format == 'numpy'


def test_composition_parity_with_docwrap():
    def target(foo, bar=1, base=None):
        """Return the log of the quux."""

    options = {'format': 'numpy', 'inheritparams': source}
    rendered = docrender(target, **options)
    docwrap(**options)(target)
    assert rendered == target.__doc__


def test_an_unknown_argument_names_the_function_called():
    with pytest.raises(DocShareError, match='docrender'):
        docrender('Summary.', inheritnonsense=True)
    with pytest.raises(DocShareError, match='doccompose'):
        doccompose('Summary.', inheritnonsense=True)


def test_none_is_rejected():
    with pytest.raises(DocShareError):
        docrender(None)
    with pytest.raises(DocShareError):
        doccompose(None)


def test_the_target_is_not_written_to_the_cache():
    # The documentation given is parsed afresh; only a source is cached, so
    # with no source the cache does not move at all.
    before = set(docshare.doccache)
    docrender(TARGET_TEXT, format='numpy')
    doccompose(TARGET_TEXT, format='numpy')
    assert set(docshare.doccache) == before


class _Holder:
    """A class with a method whose docstring cannot be replaced."""

    @classmethod
    def value(cls):
        """The value."""
        return 1


def test_an_object_with_an_unwritable_docstring_can_still_be_rendered():
    # `docwrap` must install the result, so it refuses; `docrender` installs
    # nothing, so it does not have to.
    with pytest.raises(DocShareError):
        docwrap(_Holder.value, format='numpy', inheritdescription=source)
    assert docrender(_Holder.value) == 'The value.'
