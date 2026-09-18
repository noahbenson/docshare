# `docshare`

[![tests](https://github.com/noahbenson/docshare/actions/workflows/tests.yml/badge.svg)](https://github.com/noahbenson/docshare/actions/workflows/tests.yml)
[![docs](https://github.com/noahbenson/docshare/actions/workflows/docs.yml/badge.svg)](https://noahbenson.github.io/docshare/)
[![PyPI](https://img.shields.io/pypi/v/docshare.svg)](https://pypi.org/project/docshare/)
[![Python versions](https://img.shields.io/pypi/pyversions/docshare.svg)](https://pypi.org/project/docshare/)

Share documentation between related Python objects, without repeating
yourself and without templating.

**[Read the documentation](https://noahbenson.github.io/docshare/)**

## What it does

`docshare` parses NumPy- and Google-style docstrings, lets a function inherit
the parts it would otherwise duplicate, and writes the result back to
`__doc__` as ordinary documentation. Nothing downstream needs to know:
`help`, your editor, and Sphinx all see a normal docstring.

The library is `docshare`; its decorator is `docwrap`, which wraps one
object's documentation around another's.

```python
from docshare import docwrap


def quuxatize(foo, bar=1):
    """A function that quuxizes the arguments `foo` and `bar`.

    Parameters
    ----------
    foo : float
        The foo parameter for the quux operation.
    bar : float, optional
        The bar parameter for the quux operation; the default is 1.
    """


@docwrap(format='numpy', inheritparams=quuxatize)
def logquuxatize(foo, bar=1, base=None):
    """Returns the log of the quux of arguments `foo` and `bar`.

    Parameters
    ----------
    base : float, optional
        The base of the log that should be used; the default is ``None``.
    """
```

`logquuxatize` now documents `foo`, `bar` and `base`, in signature order, and
nothing in the result hints that any of it was shared.

A source needs no decoration and no cooperation of any kind. It needs a
docstring --- including one from a library that has never heard of
`docshare`:

```python
import numpy

from docshare import docwrap


@docwrap(format='numpy', inheritparams=numpy.sum, extraparam='axis')
def total(a, axis=None):
    """Sum an array, the way we like it."""
```

## The one rule

> **Inherited documentation fills gaps. It never replaces what you wrote.**

Inheritance is always requested explicitly --- `docshare` never infers it
from class hierarchies or call graphs --- and it happens once, when the
decorator runs.

## Installation

```console
$ pip install docshare
```

Python 3.10 and later. **No runtime dependencies.**

## At a glance

* Reads and writes both NumPy and Google style, and converts between them.
* Understands the full numpydoc section set, and preserves sections it does
  not understand rather than discarding them.
* Inherits parameters, returns, raises, attributes and the rest, from one
  source or several, with renaming, exclusion and per-item binding.
* Keeps grouped declarations such as `x, y : float` intact.
* Checks documented parameters against the callable's signature.
* Works with functions, methods, classes, properties, static methods and
  class methods.
* Safe to use from several threads.

## Documentation

The full documentation lives at
**<https://noahbenson.github.io/docshare/>**:

* [Quick start](https://noahbenson.github.io/docshare/quickstart.html)
* [Guide](https://noahbenson.github.io/docshare/guide/index.html) --- every
  way to say what to inherit, how the two formats are read and written,
  signature checking, threads, and errors
* [API reference](https://noahbenson.github.io/docshare/api.html)
* [Coming from `docrep`](https://noahbenson.github.io/docshare/migrating.html)

The [specification](docs/spec.md) is the normative description the
implementation is checked against, and [`docs/deferred.md`](docs/deferred.md)
records the edge cases that were considered and how each was settled.

## Development

```console
$ pip install -e '.[dev]'
$ pytest
$ ruff check . && ruff format --check .
$ make -C docs html
```

## License

MIT. See [LICENSE](LICENSE).
