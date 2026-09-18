# Coming from docrep

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

## Rough equivalents

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

## Differences worth knowing

**No interpolation.**
: Nothing is substituted into your docstring, so a literal `%` needs no
  escaping and a missing key cannot silently vanish.

**No registration.**
: A source is any object with a docstring. It does not need decorating, and
  it does not need to be yours --- a function from NumPy or from any other
  library works.

**`keep_params` is usually unnecessary.**
: `docshare` inherits only the parameters the decorated object actually has,
  so a source with extra parameters needs no filtering.

**Placement is automatic.**
: Inherited parameters are ordered by your signature rather than by where you
  put the substitution.

**Google style is supported.**
: `docrep` is NumPy only.

**Summaries and descriptions are never inherited.**
: `docrep` can copy them explicitly; `docshare` treats them as yours.

**Your signature is checked.**
: Documentation naming a parameter you do not have is reported rather than
  passed through. See {doc}`guide/signatures`.
