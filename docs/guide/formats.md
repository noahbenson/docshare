# Formats

`docshare` reads and writes both NumPy and Google style, and detects which
one a docstring uses. The two produce the same internal representation, so a
Google-style function can inherit from a NumPy-style one and still be written
in its own style.

```python
from docshare import docwrap


def numpy_source(x, y):
    """A source written in NumPy style.

    Parameters
    ----------
    x : int
        The x, as the NumPy-style source describes it.
    y : int
        The y, as the NumPy-style source describes it.
    """
    pass


@docwrap(inheritparams=numpy_source)
def f(x, y):
    """Written in Google style.

    Args:
        y (int): My own y.
    """
    pass


assert 'Args:' in f.__doc__
assert 'x (int): The x, as the NumPy-style source describes it.' in f.__doc__
assert 'My own y.' in f.__doc__
```

## `format` and `render`

`format` says what a docstring *is*; `render` says what to write.

```python
@docwrap(format='numpy', render='google', inheritparams=numpy_source)
def g(x, y):
    """Written in NumPy style, written out in Google style.

    Parameters
    ----------
    y : int
        My own y.
    """
    pass


assert 'Args:' in g.__doc__
assert 'Parameters\n----------' not in g.__doc__
```

`render` defaults to `format`, or to the detected format when `format` was
not given. Giving `render` alone says how to write an object that has no
docstring to detect a format from:

```python
@docwrap(render='numpy', inheritparams=numpy_source)
def h(x, y):
    pass


assert h.__doc__.startswith('Parameters\n----------')
```

A docstring `docshare` cannot place --- one that mixes both styles, or an
object with no docstring at all and no `render` --- is an error rather than a
guess.

## Items with no type

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

Recognizing that prose is a **heuristic**, and deliberately a narrow one. A
type cannot be told from a phrase by its shape: English words are valid
Python identifiers, so `The computed result` is built exactly like
`array_like of float`. What separates them is that a type is a noun phrase
and never closes a sentence. So a declaration that gives no name is read as a
description **only when it ends with `.`, `?`, or `!`**, and anything else
keeps its meaning as a type. Types such as `float`, `int, optional`,
`list of str`, `array_like of float, shape (n,)`, `Sequence[int]`,
`{'a', 'b'}`, and ``:class:`numpy.ndarray``` are all unaffected. A type
written with a trailing full stop would be misread, which is the price of the
rule.

## One ambiguity worth knowing about

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
@docwrap(format='numpy', ...)    or say which format the docstring is in
```

A parameter with a type is never ambiguous, so this only arises for a
dangling colon.

## Keyword arguments

Google style has a `Keyword Args:` section; the NumPy standard does not, and
documents keyword arguments in `Parameters`. The distinction is kept in the
model, so a Google document round-trips with it intact, and is merged only
when writing NumPy.
