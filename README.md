# `docshare`

[![tests](https://github.com/noahbenson/docshare/actions/workflows/tests.yml/badge.svg)](https://github.com/noahbenson/docshare/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/docshare.svg)](https://pypi.org/project/docshare/)
[![Python versions](https://img.shields.io/pypi/pyversions/docshare.svg)](https://pypi.org/project/docshare/)

Share documentation between related Python objects, without repeating
yourself and without templating.

The library is `docshare`; its decorator is `docwrap`, which wraps one
object's documentation around another's.

`docshare` parses NumPy- and Google-style docstrings, lets a function inherit
the parts it would otherwise duplicate, and writes the result back to
`__doc__` as ordinary documentation. Nothing downstream needs to know: `help`,
your IDE, and Sphinx all see a normal docstring.

It is pure Python and has no runtime dependencies.

## Installation

```console
$ pip install docshare
```

`docshare` supports Python 3.10 and later.

## Quick start

Two functions, the second a variation on the first:

```python
from docshare import docwrap


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
    return (foo * bar) ** (foo + bar)


@docwrap(format='numpy', inheritparams=quuxatize)
def logquuxatize(foo, bar=1, base=None):
    """Returns the log of the quux of arguments `foo` and `bar`.

    Parameters
    ----------
    base : float, optional
        The base of the log that should be used; the default is ``None``.

    Returns
    -------
    float
        The log-quux result.
    """
```

`logquuxatize` now documents all three of its parameters:

```text
Returns the log of the quux of arguments `foo` and `bar`.

Parameters
----------
foo : float
    The foo parameter for the quux operation.
bar : float, optional
    The bar parameter for the quux operation; the default is 1.
base : float, optional
    The base of the log that should be used; the default is ``None``.

Returns
-------
float
    The log-quux result.
```

`foo` and `bar` were inherited; `base` is the function's own. They appear in
signature order, and nothing in the result hints that any of it was shared.

## The one rule

> **Inherited documentation fills gaps. It never replaces what you wrote.**

Everything else follows from that. If the decorated object documents a
parameter, that documentation stays. If it does not, a source may supply one.
Inheritance is always requested explicitly --- `docshare` never infers it from
class hierarchies or call graphs --- and it happens once, when the decorator
runs.

## Inheriting

### Several sources

Sources are tried right to left, so the last one wins:

```python
@docwrap(format='numpy', inheritparams=(base, mixin, override))
def f(x, y):
    """..."""
```

For each parameter: whatever `f` documents itself, else `override`, else
`mixin`, else `base`.

### One item from one source

Bind a source to a single item by pairing it with that item's name. This wins
regardless of source order:

```python
@docwrap(format='numpy', inheritparams=(base, mixin, (base, 'x')))
def f(x, y):
    """..."""
```

`x` now always comes from `base`; everything else follows the usual order. A
source is an object with documentation and never a bare string or integer, so
`(base, mixin)` is unambiguously two sources while `(base, 'x')` is one
binding.

### Skipping and renaming

`dropparams` names one of your own parameters and excludes it from
inheritance. It does not remove documentation the object wrote for itself:

```python
@docwrap(format='numpy', inheritparams=base, dropparams='internal')
def f(x, internal=None):
    """..."""
```

`parammap` maps *this object's* parameter names to the *source's*, for APIs
that name the same idea differently:

```python
@docwrap(format='numpy', inheritparams=base, parammap={'input': 'x'})
def f(input, scale=1):
    """..."""
```

### Parameters your signature does not show

A parameter taken from `**kwargs` is invisible to the signature, so say so
explicitly. `docshare` will not infer it: if the presence of `**kwargs`
excused undeclared parameters, it would excuse every typo too.

```python
@docwrap(format='numpy', extraparam='null')
def f(**kwargs):
    """...

    Parameters
    ----------
    null : bool
        ...
    """
```

### Returns, raises, and the rest

Every section `docshare` understands works the same way. Items in `Returns`
and `Yields` are identified by name when they have one and by position when
they do not; items in `Raises` and `Warns` are identified by their exception
type.

```python
@docwrap(format='numpy', inheritreturns=base, ignorereturns=(0, 2))
def f():
    """..."""
```

If `base` documents four return values, this takes the second and fourth.

Because an unnamed return value has nothing to identify it, an object that
documents one *and* inherits that section must say which inherited item it
replaces:

```python
@docwrap(format='numpy', inheritreturns=base, returnmap={0: 2})
def f():
    """...

    Returns
    -------
    float
        Replaces the source's third return value.
    """
```

Left ambiguous, that is an error rather than a guess.

### Everything at once

```python
@docwrap(format='numpy', inheritall=base)
def f(x, y):
    """..."""
```

`inheritall` takes every section `docshare` recognizes. It deliberately
leaves unrecognized sections alone; add `inheritother=True` to include those
too.

### Sections `docshare` has never heard of

An unrecognized section is preserved wherever it appears, but is never
inherited unless you name it:

```python
@docwrap(format='numpy', inheritother=[(base, 'Efferents')])
def f(x, y):
    """..."""
```

### Grouped parameters

A declaration may document several names at once:

```text
Parameters
----------
x, y : float
    Cartesian coordinates.
```

That is one documentation item, and it stays one. A group is inherited whole
or not at all: documenting only `x` yourself while inheriting the group is an
error, because the result would either contradict what you wrote or document
a parameter you do not have. Renaming through `parammap` is fine so long as
every member still corresponds to one of your parameters.

## Arguments

`docwrap` accepts these in addition to the per-section arguments below.

| Argument | Meaning |
|---|---|
| `format` | The format the object's own docstring is written in. Detected by default. |
| `render` | The format to write the result in. Defaults to `format`, or to the detected format. |
| `inherit` | The general form: `inherit={'Parameters': base}`. |
| `inheritall` | Inherit every recognized section from these sources. |
| `inheritother` | Inherit named unrecognized sections, or `True` alongside `inheritall`. |
| `extraparam` | Parameters that are documented deliberately but absent from the signature. |

Every section accepts `inherit<short>`. Every section that holds items also
accepts `<singular>map` and one argument that excludes an item from
inheritance --- named for the side it acts on, since the two sides are never
interchangeable:

* **`drop<short>`** names one of *your* parameters. The sections that
  document a callable's parameters are ordered by its signature, so you say
  which of your own parameters should not receive inherited documentation.
  It does not remove documentation you wrote yourself.
* **`ignore<short>`** names one of the *source's* items. Every other section
  is driven by its sources --- there is no signature listing your return
  values --- so you say which of the source's items not to take.

There is no `ignoreparams` and no `ignorereturns` of the other kind, because
each would do nothing: a source parameter you do not have is never inherited
anyway, and your own documentation is kept regardless.

| Section | Inherit | Exclude | Map |
|---|---|---|---|
| Parameters / Args | `inheritparams` | `dropparams` | `parammap` |
| Other Parameters | `inheritotherparams` | `dropotherparams` | `otherparammap` |
| Keyword Args | `inheritkeywordargs` | `dropkeywordargs` | `keywordargmap` |
| Returns | `inheritreturns` | `ignorereturns` | `returnmap` |
| Yields | `inherityields` | `ignoreyields` | `yieldmap` |
| Receives | `inheritreceives` | `ignorereceives` | `receivemap` |
| Raises | `inheritraises` | `ignoreraises` | `raisemap` |
| Warns | `inheritwarns` | `ignorewarns` | `warnmap` |
| Attributes | `inheritattributes` | `ignoreattributes` | `attributemap` |
| Methods | `inheritmethods` | `ignoremethods` | `methodmap` |
| Warnings | `inheritwarnings` | --- | --- |
| See Also | `inheritseealso` | --- | --- |
| Notes | `inheritnotes` | --- | --- |
| References | `inheritreferences` | --- | --- |
| Examples | `inheritexamples` | --- | --- |

The last five hold prose rather than items. They are inherited whole, and
only when you have no section of that kind; prose is never merged.

## Formats

`docshare` reads and writes both NumPy and Google style, and detects which
one a docstring uses. The two produce the same internal representation, so a
Google-style function can inherit from a NumPy-style one and still be written
in its own style.

```python
@docwrap(inheritparams=numpy_style_source)
def f(x, y):
    """Written in Google style.

    Args:
        y (int): My own y.
    """
```

`format` says what a docstring *is*; `render` says what to write. Give both
to convert:

```python
@docwrap(format='numpy', render='google', inheritparams=base)
def f(x, y):
    """..."""
```

A docstring `docshare` cannot place --- one that mixes both styles, or an
object with no docstring at all and no `render` --- is an error rather than a
guess.

### Items with no type

Google style lets a return value, a raised error, or a warning be described
without naming its type. The NumPy standard does not: its specification says
of `Returns` that "the type of each return value is always required", and
repeats that for `Yields`. Converting therefore has to supply one, and
`docshare` writes the least specific type of the relevant hierarchy, which
asserts no more than the author did:

| Section | supplied type |
|---|---|
| `Returns`, `Yields` | `object` |
| `Raises` | `Exception` |
| `Warns` | `Warning` |

```text
Returns:                    →    Returns
    The computed result.         -------
                                 object
                                     The computed result.
```

Two consequences are worth knowing. Converting back to Google keeps the
supplied type, so a document that made the round trip says
`object: The computed result.` --- nothing is lost, but it is not the
original text. And reading a NumPy docstring that puts prose where a type
belongs, which the standard does not allow, understands it as a description
and writes it back with a type. Both leave a docstring saying more than it
did, never less.

Recognizing that prose is a **heuristic**, and deliberately a narrow one.
A type cannot be told from a phrase by its shape --- English words are valid
Python identifiers, so `The computed result` is built exactly like
`array_like of float`. What separates them is that a type is a noun phrase
and never closes a sentence. So a declaration that gives no name is read as
a description **only when it ends with `.`, `?`, or `!`**, and anything else
keeps its meaning as a type. Types such as `float`, `int, optional`,
`list of str`, `array_like of float, shape (n,)`, `Sequence[int]`, `{'a',
'b'}`, and ``:class:`numpy.ndarray``` are all unaffected. A type written
with a trailing full stop would be misread, which is the price of the rule.

### One ambiguity worth knowing about

A NumPy parameter written with an empty type has exactly the shape of a
Google section header:

```text
Parameters
----------
method :
    Which method to use.
```

`method :` could be a parameter with no type, or the start of a Google
`method:` section. If the name also happens to be one `docshare` recognizes
as a section --- `method`, `args`, `params`, `returns`, `attributes`,
`notes`, and a few dozen others --- detection reports the ambiguity instead
of choosing.

Any of three things resolves it, and the error message says so:

```text
method : str                     give the parameter a type
method                           or drop the colon
@docwrap(format='numpy', ...)   or say which format the docstring is in
```

A parameter with a type is never ambiguous, so this only arises for a
dangling colon.

## Reading documentation

```python
from docshare import docparse, docinfo
```

`docparse(obj)` parses the object's current documentation from scratch and
returns a `Document`: a summary, a description, and an ordered sequence of
sections, each holding items or text. The representation is immutable and
does not depend on which format it was written in.

`docinfo(obj)` answers from a cache instead, parsing only when it has nothing
recorded. For an object `docwrap` has decorated, that record is the
*composed* document --- everything inheritance assembled, not just what the
original docstring said --- which is what makes chains of inheritance work.

Both accept a docstring directly, which is convenient for experimenting:

```python
from docshare import docparse

doc = docparse('''Summary.

    Parameters
    ----------
    x : int
        The x.
    ''')
assert doc.section('parameters').items[0].names == ('x',)
```

## When something is wrong

`docshare` prefers an error to a guess. Every exception derives from
`DocShareError`:

| Exception | Raised when |
|---|---|
| `DocParseError` | A docstring cannot be read in the format required. |
| `DocFormatError` | A format is unsupported, ambiguous, or missing. |
| `DocInheritanceError` | The requested inheritance is incoherent. |
| `DocMappingError` | A mapping or a bound source is invalid. |
| `DocSignatureError` | Documentation describes a parameter the object lacks. |

Messages are meant to be actionable. A misspelled parameter, for instance:

```text
the documentation of f(x, y=1) describes a parameter 'scal' in its
'Parameters' section, but f has no such parameter. Correct the name, or, if
it is documented deliberately because it is taken from **kwargs, declare it
with extraparam='scal'
```

## Coming from `docrep`

[`docrep`](https://github.com/Chilipp/docrep) solves the same problem by
templating: you register a docstring's sections under a key and interpolate
them into another docstring with `%(key.parameters)s`. `docshare` does it by
composition instead --- you name the object to inherit from, and it works out
which items apply.

```python
# docrep
from docrep import DocstringProcessor
docstrings = DocstringProcessor()

@docstrings.get_sectionsf('base')
@docstrings.dedent
def base(x, y):
    """..."""

@docstrings.dedent
def derived(x, y, z):
    """Summary.

    Parameters
    ----------
    %(base.parameters)s
    z : int
        The z.
    """
```

```python
# docshare
from docshare import docwrap

@docwrap(format='numpy')
def base(x, y):
    """..."""

@docwrap(format='numpy', inheritparams=base)
def derived(x, y, z):
    """Summary.

    Parameters
    ----------
    z : int
        The z.
    """
```

Roughly:

| `docrep` | `docshare` |
|---|---|
| `DocstringProcessor()` instance | nothing; no shared state |
| `@docstrings.get_sectionsf('key')` | nothing; any documented object is a source |
| `%(key.parameters)s` | `inheritparams=source` |
| `@docstrings.dedent` | nothing; docstrings are always dedented |
| `delete_params('key', 'a')` | `dropparams='a'` |
| `keep_params('key', 'a')` | usually nothing --- see below |
| `delete_kwargs`, `delete_types` | `dropparams`, or document explicitly |
| `get_summary`, `get_extended_summary` | nothing; summaries are never inherited |

Differences worth knowing:

* **No interpolation.** Nothing is substituted into your docstring, so a
  literal `%` needs no escaping and a missing key cannot silently vanish.
* **`keep_params` is usually unnecessary.** `docshare` inherits only the
  parameters the decorated object actually has, so a source with extra
  parameters needs no filtering.
* **Placement is automatic.** Inherited parameters are ordered by your
  signature rather than by where you put the substitution.
* **Google style is supported**, and `docrep` is NumPy only.
* **Summaries and descriptions are never inherited.** `docrep` can copy them
  explicitly; `docshare` treats them as yours.
* **Your signature is checked.** Documentation naming a parameter you do not
  have is reported rather than passed through.

## What `docshare` does not do

It does not generate documentation, replace Sphinx or its Napoleon
extension, interpret type expressions, or understand the markup inside a
description. It reads enough structure to compose docstrings reliably and
leaves everything else exactly as written.

See [`docs/spec.md`](docs/spec.md) for the specification and
[`docs/deferred.md`](docs/deferred.md) for known edge cases.

## Development

```console
$ pip install -e '.[dev]'
$ pytest
$ ruff check . && ruff format --check .
```

## License

MIT. See [LICENSE](LICENSE).
