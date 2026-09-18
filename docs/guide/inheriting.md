# Inheriting

Every inheritance is requested explicitly, by naming the object to inherit
from. A source needs no decoration and no cooperation; it needs a docstring.

## Several sources

Sources are tried right to left, so the last one wins:

```python
@docwrap(format='numpy', inheritparams=(base, mixin, override))
def f(x, y):
    """..."""
```

For each parameter: whatever `f` documents itself, else `override`, else
`mixin`, else `base`.

## One item from one source

Bind a source to a single item by pairing it with that item's name. The
binding wins regardless of source order:

```python
@docwrap(format='numpy', inheritparams=(base, mixin, (base, 'x')))
def f(x, y):
    """..."""
```

`x` now always comes from `base`; everything else follows the usual order.

A source is an object with documentation, never a bare string or integer, so
`(base, mixin)` is unambiguously two sources while `(base, 'x')` is one
binding. In a section whose items are identified by position, such as
`Returns`, the key may be a position instead; in a section identified by
name, a position identifies nothing and is reported as an error.

## A source whose format must be stated

A source is ordinarily an object, and its format is detected from its
docstring. Where that will not do --- because the docstring is ambiguous, or
because you want to be explicit --- parse it yourself and hand over the
result:

```python
from docshare import docparse, docwrap


@docwrap(format='numpy', inheritparams=docparse(base, format='google'))
def f(x, y):
    """..."""
```

Anywhere a source is accepted, an already-parsed
{py:class}`~docshare.Document` is accepted too: on its own, inside a
sequence, as the first half of a `(source, key)` binding, and as
`inheritall`.

## Skipping

Two arguments exclude an item from inheritance, and which one a section
offers depends on which side decides what exists.

`drop<short>`
: Names one of *your* parameters. The sections that document a callable's
  parameters are ordered by its signature, so you say which of your own
  parameters should not receive inherited documentation. It does not remove
  documentation you wrote yourself.

`ignore<short>`
: Names one of the *source's* items. Every other section is driven by its
  sources --- there is no signature listing your return values --- so you say
  which of the source's items not to take.

```python
@docwrap(format='numpy', inheritparams=base, dropparams='internal')
def f(x, internal=None):
    """..."""


@docwrap(format='numpy', inheritreturns=base, ignorereturns=(0, 2))
def g():
    """..."""
```

There is no `ignoreparams` and no `dropreturns`, because each would do
nothing: a source parameter you do not have is never inherited anyway, and
your own documentation is kept regardless. Using the wrong one is an error
that names the right one.

## Renaming

`parammap` maps *your* parameter names to the *source's*, for APIs that name
the same idea differently:

```python
@docwrap(format='numpy', inheritparams=base, parammap={'input': 'x'})
def f(input, scale=1):
    """..."""
```

Every section that holds items has an equivalent: `returnmap`, `raisemap`,
`attributemap`, and so on. The direction is always *your* identity to the
*source's*.

## Parameters your signature does not show

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

A declared extra parameter takes part in inheritance like any other.

## Returns, raises, and the rest

Every section `docshare` understands works the same way. Items in `Returns`
and `Yields` are identified by name when they have one and by position when
they do not; items in `Raises` and `Warns` are identified by their exception
type.

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

## Everything at once

```python
@docwrap(format='numpy', inheritall=base)
def f(x, y):
    """..."""
```

`inheritall` takes every section `docshare` recognizes. It deliberately
leaves unrecognized sections alone; add `inheritother=True` to include those
too.

## Sections `docshare` has never heard of

An unrecognized section is preserved wherever it appears, but is never
inherited unless you name it:

```python
@docwrap(format='numpy', inheritother=[(base, 'Efferents')])
def f(x, y):
    """..."""
```

## The general form

The per-section arguments are shorthand. The general form names sections
directly:

```python
@docwrap(format='numpy', inherit={'Parameters': base, 'Returns': base})
def f(x, y):
    """..."""
```

Naming a section in both places is an error rather than a silent precedence
rule.

## Composition happens once

Composition runs when the decorator runs, and nothing is recomputed
afterwards. Changing a source's `__doc__` later does not propagate, and a
docstring assigned by a later decorator is outside `docshare`'s control.

A composed object is itself a source, and offers everything composition
assembled rather than only what its own docstring said, so chains work:

```python
@docwrap(format='numpy', inheritparams=base)
def middle(x):
    """..."""


@docwrap(format='numpy', inheritparams=middle)
def leaf(x):
    """..."""
```
