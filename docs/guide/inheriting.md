# Inheriting

Every inheritance is requested explicitly, by naming the object to inherit
from. A source needs no decoration and no cooperation; it needs a docstring.

The examples on this page all use these three, which are ordinary
undecorated functions:

```python
from docshare import docparse, docwrap


def base(x, y):
    """Do the basic thing.

    Parameters
    ----------
    x : int
        The x, as base describes it.
    y : int
        The y, as base describes it.

    Returns
    -------
    int
        The first result.
    int
        The second result.

    Efferents
    ---------
    Connections to downstream objects.
    """
    pass


def mixin(x, y):
    """Do it another way.

    Parameters
    ----------
    x : int
        The x, as mixin describes it.
    """
    pass


def override(x, y):
    """Do it a third way.

    Parameters
    ----------
    x : int
        The x, as override describes it.
    """
    pass
```

## Several sources

Sources are tried right to left, so the last one wins:

```python
@docwrap(format='numpy', inheritparams=(base, mixin, override))
def f(x, y):
    """Do our thing."""
    pass


assert 'The x, as override describes it.' in f.__doc__
assert 'The y, as base describes it.' in f.__doc__
```

For each parameter: whatever `f` documents itself, else `override`, else
`mixin`, else `base`.

## One item from one source

Bind a source to a single item by pairing it with that item's name. The
binding wins regardless of source order:

```python
@docwrap(format='numpy', inheritparams=(base, mixin, override, (base, 'x')))
def f(x, y):
    """Do our thing."""
    pass


assert 'The x, as base describes it.' in f.__doc__
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
@docwrap(format='numpy', inheritparams=docparse(base, format='numpy'))
def f(x, y):
    """Do our thing."""
    pass


assert 'The x, as base describes it.' in f.__doc__
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
@docwrap(format='numpy', inheritparams=base, dropparams='y')
def f(x, y):
    """Do our thing."""
    pass


assert 'The x, as base describes it.' in f.__doc__
assert 'The y, as base describes it.' not in f.__doc__


@docwrap(format='numpy', inheritreturns=base, ignorereturns=0)
def g():
    """Do our thing."""
    pass


assert 'The second result.' in g.__doc__
assert 'The first result.' not in g.__doc__
```

There is no `ignoreparams` and no `dropreturns`, because each would do
nothing: a source parameter you do not have is never inherited anyway, and
your own documentation is kept regardless. Using the wrong one is an error
that names the right one.

## Renaming

`parammap` maps *your* parameter names to the *source's*, for APIs that name
the same idea differently:

```python
@docwrap(format='numpy', inheritparams=base, parammap={'first': 'x'})
def f(first, scale=1):
    """Do our thing."""
    pass


assert 'first : int' in f.__doc__
assert 'The x, as base describes it.' in f.__doc__
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
    """Do our thing.

    Parameters
    ----------
    null : bool
        Whether to do nothing at all.
    """
    pass


assert 'null : bool' in f.__doc__
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
@docwrap(format='numpy', inheritreturns=base, returnmap={0: 1})
def f():
    """Do our thing.

    Returns
    -------
    int
        Our own account of the second result.
    """
    pass


assert 'The first result.' in f.__doc__
assert 'Our own account of the second result.' in f.__doc__
```

Left ambiguous, that is an error rather than a guess.

## Everything at once

```python
@docwrap(format='numpy', inheritall=base)
def f(x, y):
    """Do our thing."""
    pass


assert 'The x, as base describes it.' in f.__doc__
assert 'The first result.' in f.__doc__
assert 'Efferents' not in f.__doc__
```

`inheritall` takes every section `docshare` recognizes, along with the
source's summary and description. It deliberately leaves unrecognized
sections alone; add `inheritother=True` to include those too.

## The summary and the description

The text above the first section is two things: the summary, which is the
opening paragraph, and the description, which is whatever prose follows it.
Neither is a section, so neither is inherited by inheriting one --- taking a
source's `Parameters` never takes its first line as well.

Ask for them by name, or take both with `inheritall`:

```python
@docwrap(format='numpy', inheritsummary=base, inheritparams=base)
def f(x, y):
    pass


assert f.__doc__.startswith('Do the basic thing.')
assert 'The x, as base describes it.' in f.__doc__
```

`inheritdescription` does the same for the prose beneath the summary, and
`inheritall` implies both.

As everywhere else, what you write yourself wins: a function with a summary
of its own keeps it, and `inheritsummary` does nothing.

```python
@docwrap(format='numpy', inheritall=base)
def f(x, y):
    """Do our thing."""
    pass


assert f.__doc__.startswith('Do our thing.')
```

This is worth reaching for when a wrapper really is the thing it wraps.
Where it is not --- and a wrapper usually has something of its own to say
--- write the summary and let the sections be inherited.

### Docstrings that open with a call signature

Some documentation opens with the object's own call signature rather than a
summary. NumPy's ufuncs are the common example:

```text
log(x, /, out=None, *, where=True, ...[, signature])

Natural logarithm, element-wise.
```

That line describes exactly one object, so `docshare` does not read it as a
summary. It is kept aside, written back out when that object's own docstring
is rendered, and never inherited by anything else; `inheritsummary=np.log`
gives you `Natural logarithm, element-wise.` rather than a signature that
belongs to something else.

## Sections `docshare` has never heard of

An unrecognized section is preserved wherever it appears, but is never
inherited unless you name it:

```python
@docwrap(format='numpy', inheritother=[(base, 'Efferents')])
def f(x, y):
    """Do our thing."""
    pass


assert 'Connections to downstream objects.' in f.__doc__
```

## The general form

The per-section arguments are shorthand. The general form names sections
directly:

```python
@docwrap(format='numpy', inherit={'Parameters': base, 'Returns': base})
def f(x, y):
    """Do our thing."""
    pass


assert 'The x, as base describes it.' in f.__doc__
assert 'The first result.' in f.__doc__
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
def middle(x, y):
    """Do the middling thing."""
    pass


@docwrap(format='numpy', inheritparams=middle)
def leaf(x, y):
    """Do the leafy thing."""
    pass


assert 'The x, as base describes it.' in leaf.__doc__
```
