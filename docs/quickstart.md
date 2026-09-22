# Quick start

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
    pass
```

`logquuxatize.__doc__` is now:

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
signature order.

## What just happened

1. Both docstrings were parsed into a representation that does not depend on
   which format they were written in.
2. `logquuxatize` documents `base` itself, so that stayed. It documents
   neither `foo` nor `bar`, so those were taken from `quuxatize`.
3. The parameters were ordered by `logquuxatize`'s own signature.
4. The result was written back to `__doc__` as an ordinary docstring.

Nothing about the result requires `docshare` to read it.

## Decorating without inheriting

Used bare, `docwrap` parses and checks the docstring and leaves it exactly as
written, down to its whitespace:

```python
from docshare import docwrap


@docwrap
def area(width, height):
    """Compute an area.

    Parameters
    ----------
    width : float
        The width.
    height : float
        The height.
    """
    return width * height
```

That is worth doing for the check alone: a parameter documented under the
wrong name is reported when the module is imported, rather than going
unnoticed. See {doc}`guide/signatures`.

## Where to go next

* {doc}`guide/inheriting` --- every way to say what to inherit.
* {doc}`guide/formats` --- how the two styles are read and written.
* {doc}`guide/reading` --- parsing documentation without decorating anything.
* {doc}`guide/standalone` --- composing and rendering documentation without
  decorating anything.
* {doc}`migrating` --- coming from `docrep`.
