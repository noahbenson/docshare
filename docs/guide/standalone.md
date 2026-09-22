# Without decorating

`docwrap` composes an object's documentation and installs it on the object.
Two functions do the same work without an object to install it on, which is
useful for previewing a docstring, for generating one, or for composing
documentation that is never attached to anything:

```python
from docshare import docrender


def quuxatize(foo, bar=1):
    """Returns the quux of arguments `foo` and `bar`.

    Parameters
    ----------
    foo : float
        The foo parameter.
    bar : float, optional
        The bar parameter.
    """


target = '''Returns the log of the quux.

    Parameters
    ----------
    base : float, optional
        The base of the log.
    '''

text = docrender(target, format='numpy', inheritparams=quuxatize)
assert 'foo : float' in text
assert 'bar : float, optional' in text
assert 'base : float, optional' in text
```

`docrender` accepts every argument `docwrap` does, meaning the same thing, and
returns the rendered docstring as a string instead of replacing a `__doc__`.
{doc}`inheriting` therefore describes all of these two functions' arguments as
well; only where the object goes is different.

## The composed document

`doccompose` stops one step earlier and returns the
{py:class}`~docshare.Document` that `docrender` would render:

```python
from docshare import doccompose

doc = doccompose(target, format='numpy', inheritparams=quuxatize)
assert [item.names for item in doc.section('parameters').items] == [
    ('base',),
    ('foo',),
    ('bar',),
]
```

Use it when the model is what you want --- to inspect or post-process the
sections, for instance --- rather than the text.

## What you can give them

The first argument may be a docstring, an object, or an already-parsed
{py:class}`~docshare.Document`:

```python
from docshare import docparse, docrender

assert docrender(target, inheritparams=quuxatize) == docrender(
    docparse(target), inheritparams=quuxatize
)
```

An object is more than a docstring, because its signature is available:

```python
def logquuxatize(foo, bar=1, base=None):
    """Returns the log of the quux."""
    pass


text = docrender(logquuxatize, format='numpy', inheritparams=quuxatize)
assert 'foo : float' in text
assert 'bar : float, optional' in text
assert 'base' not in text
```

A string or a `Document` has no signature, so no validation is attempted and a
section of parameters is ordered by the documentation itself and its sources
instead. Two consequences follow, and both are the same behavior `docwrap`
already has for an object whose signature cannot be read:

* Nothing is checked against a signature, so `docrender` never raises
  {py:exc}`~docshare.DocSignatureError` for a string or a `Document`.
* A parameter section is driven by its sources, so a source parameter that
  the documentation does not mention **is** inherited. With the object above,
  `base` was left out; with the string `target`, every parameter the source
  documents is added.

## Rendering is a rewrite

`docrender` always renders, even when nothing was inherited, so its result is
not necessarily its input: rendering normalizes indentation, the blank lines
between sections, and the spelling of a recognized section's title. Asking for
another format with `render=` converts the documentation:

```python
text = docrender(target, format='numpy', render='google')
assert 'Args:' in text
assert 'Parameters\n----------' not in text
```

Because neither function assigns anything, both work on objects whose
`__doc__` cannot be written --- a `classmethod`, a built-in type, a class
whose instances are read-only --- where `docwrap` reports an error. Neither
writes to the cache either; the documentation you pass is parsed afresh, and
only a source is read through {py:data}`~docshare.doccache`, exactly as for
`docwrap`.
