# Signatures

`docshare` checks documented parameters against the signature of the object
they describe, when the decorator runs.

The purpose is to catch documentation that has drifted from the code --- a
renamed parameter, a typo, a parameter that was removed --- not to demand
that every parameter be documented.

## The rule

A parameter the signature accepts but the documentation omits is **not** an
error. Partial documentation is legitimate and common.

A parameter the documentation describes but the signature does not accept
**is** an error:

```text
the documentation of f(x, y=1) describes a parameter 'scal' in its
'Parameters' section, but f has no such parameter. Correct the name, or, if
it is documented deliberately because it is taken from **kwargs, declare it
with extraparam='scal'
```

Documenting the same parameter twice is also reported, naming both sections.

## `**kwargs` does not excuse anything

A signature with `**kwargs` deliberately does not license an undeclared
parameter. If it did, every function with `**kwargs` would silently accept
every misspelling, which is precisely what this check exists to catch.
Declare such parameters with `extraparam`.

## What is checked

All parameter kinds are handled: positional-only, positional-or-keyword,
keyword-only, and both variadic forms. Documentation conventionally writes
the last two as `*args` and `**kwargs` while a signature names them `args`
and `kwargs`, so the stars are stripped before matching.

A grouped declaration is validated name by name, and the error locates the
group so the offending line can be found.

The keys of `parammap` name parameters of the object being documented, and
are validated alongside. A bad key raises
{py:exc}`~docshare.DocMappingError` rather than
{py:exc}`~docshare.DocSignatureError`, because the mistake is in the
decorator argument rather than in the docstring.

## Objects without signatures

`inspect.signature` cannot handle a `classmethod` object, and a `property`
has no signature of its own; both are resolved to the function they wrap. An
object with no determinable signature is skipped rather than rejected, since
there is nothing to check against.

## Objects that can be decorated

Functions, methods, classes, properties, static methods and class methods
all work, in either decorator ordering:

```python
from docshare import docwrap


def base(p):
    """A source.

    Parameters
    ----------
    p : int
        The p, as base describes it.
    """
    pass


class Example:
    @docwrap(format='numpy', inheritparams=base)
    @staticmethod
    def above(p):
        pass

    @staticmethod
    @docwrap(format='numpy', inheritparams=base)
    def below(p):
        pass


for name in ('above', 'below'):
    member = Example.__dict__[name]
    assert 'The p, as base describes it.' in member.__doc__
    assert isinstance(member, staticmethod)
```

Both compose correctly and leave the descriptor's type intact.
