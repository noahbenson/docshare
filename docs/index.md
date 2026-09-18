# docshare

Share documentation between related Python objects, without repeating
yourself and without templating.

`docshare` parses NumPy- and Google-style docstrings, lets a function inherit
the parts it would otherwise duplicate, and writes the result back to
`__doc__` as ordinary documentation. Nothing downstream needs to know:
{py:func}`help`, your editor, and Sphinx all see a normal docstring.

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

`logquuxatize` now documents all three of its parameters, in signature
order, and nothing in the result hints that any of it was shared.

The source needs no decoration, and no cooperation of any kind. A source is
anything with a docstring, including a function from a library that has never
heard of `docshare`:

```python
import numpy

from docshare import docwrap


@docwrap(format='numpy', inheritparams=numpy.sum, extraparam='axis')
def total(a, axis=None):
    """Sum an array, the way we like it."""
```

## The one rule

> **Inherited documentation fills gaps. It never replaces what you wrote.**

Everything else follows from that. If the decorated object documents a
parameter, that documentation stays. If it does not, a source may supply one.
Inheritance is always requested explicitly --- `docshare` never infers it from
class hierarchies or call graphs --- and it happens once, when the decorator
runs.

## Contents

```{toctree}
:maxdepth: 2

installation
quickstart
guide/index
migrating
api
```

```{toctree}
:maxdepth: 1
:caption: Project

changelog
spec
deferred
```

## At a glance

* Pure Python, **no runtime dependencies**, Python 3.10 and later.
* Reads and writes both NumPy and Google style, and converts between them.
* Understands the full numpydoc section set, and preserves sections it does
  not understand rather than discarding them.
* Checks documented parameters against the callable's signature.
* Keeps grouped declarations such as `x, y : float` intact.
* Safe to use from several threads.

## Index

* {ref}`genindex`
* {ref}`modindex`
