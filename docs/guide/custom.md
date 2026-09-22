# Custom sections

`docshare` recognizes a fixed set of sections. A docstring may have others,
and a document that a library's own conventions describe may need them read
rather than merely preserved. `custom=` says so, for one call.

## Declaring a section

A declaration maps each title to the recognized section it resembles:

```python
from docshare import docparse, docwrap


def fit(w, x):
    """Fit a model.

    Parameters
    ----------
    w : array
        The fitted weights.

    Inputs
    ------
    x : array
        The observed data.
    """
    pass


doc = docparse(fit, custom={'Inputs': 'Parameters'})
assert doc.section('Inputs').items[0].names == ('x',)
assert doc.section('Parameters').items[0].names == ('w',)
```

`Inputs` is not another name for `Parameters`. The two coexist and mean
different things --- a model's parameters are fitted, its inputs are
observed --- so a declared section is a section of its own that *borrows*
how its body is read. It keeps its own title in both formats, is never
merged into what it resembles, and is never checked against the signature.

What it borrows is whether the body holds items, how those items are
identified, and what type stands in for one the author left out. Declare a
section like `Parameters` or `Attributes` for named items, like `Returns`
for positional ones, like `Raises` for ones named by an exception type, or
like `Notes` for prose.

## Declaring a section without a kind

A title given on its own declares the title to be a section and says nothing
about what it means. The body is preserved exactly and never interpreted, as
an unrecognized NumPy section is:

```python
def sender(x):
    """Send.

    Efferents:
        Connections to downstream objects.
    """
    pass


doc = docparse(sender, custom=['Efferents'])
assert doc.section('Efferents').opaque
assert doc.section('Efferents').text == ('Connections to downstream objects.',)
```

This matters mostly for Google style, which has no syntax of its own for an
unrecognized section --- see {ref}`unrecognized-sections`. A NumPy underline
needs no declaration to be a section.

## Nothing is registered

A declaration lasts for the call that makes it. Reading the same docstring
without it reads it the way it always did:

```python
assert docparse(fit).section('Inputs').opaque
assert docparse(fit, custom={'Inputs': 'Parameters'}).section('Inputs').items
```

That is deliberate. A global registry would let one library's declaration
change how another library's docstrings are read, which is exactly the kind
of action at a distance a documentation tool should not have.

## Inheriting a declared section

`custom=` on `docwrap` declares a section on the decorated object and
decides the rest of the call's vocabulary. When the title is a Python name,
it gets the same three arguments a recognized section has:

```python
@docwrap(custom={'Inputs': 'Parameters'}, format='numpy', inheritinputs=fit)
def refit(w, x):
    """Refit the model.

    Parameters
    ----------
    w : array
        Our own weights.
    """
    pass


assert 'Our own weights.' in refit.__doc__
assert 'Inputs\n------\nx : array' in refit.__doc__
assert 'The observed data.' in refit.__doc__
```

Naming `fit` in `inheritinputs` is enough to have it read with `Inputs`
declared: the argument could not mean anything otherwise.

A declared section is driven by its sources, as `Attributes` is, so its
exclusion names one of the *source's* items and is spelled `ignore`:
`inheritinputs`, `ignoreinputs`, and `inputmap`.

## Titles that are not Python names

`Model Inputs` and `Type-Hints` are perfectly good section titles and no
argument can be named after them. Every declared section is therefore also
addressable by title:

```python
def measured(a):
    """Measure.

    Model Inputs
    ------------
    a : array
        The a.
    """
    pass


@docwrap(
    custom={'Model Inputs': 'Parameters'},
    format='numpy',
    inheritcustom={'Model Inputs': measured},
)
def remeasure(a):
    """Remeasure."""
    pass


assert 'Model Inputs\n------------\na : array' in remeasure.__doc__
```

`ignorecustom` and `custommap` are its companions. A section declared
without a kind has no items to exclude or rename, so it accepts only
`inheritcustom`, which takes it whole.

## Sources: `sourcecustom` and `sourceformat`

An argument that names a declared section says which source needs it.
`inheritall` names no section, so it needs telling:

```python
@docwrap(
    custom={'Inputs': 'Parameters'},
    format='numpy',
    inheritall=fit,
    sourcecustom=True,
)
def refit_all(w, x):
    """Refit everything."""
    pass


assert 'The fitted weights.' in refit_all.__doc__
assert 'The observed data.' in refit_all.__doc__
```

`sourcecustom=True` gives every source the whole declaration. Naming sources
directly --- `sourcecustom=(fn1, fn2)` --- gives those sources the whole
declaration, and a mapping --- `sourcecustom={'Inputs': (fn1, fn2)}` ---
gives named sources one section of it.

`sourceformat` says which format a source is written in, for a docstring
whose format cannot be detected:

```python
def google_fit(w, x):
    """Fit, in Google style.

    Inputs:
        x (array): The observed data.
    """
    pass


@docwrap(
    custom={'Inputs': 'Parameters'},
    format='numpy',
    inheritinputs=google_fit,
    sourceformat={'google': google_fit},
)
def from_google(w, x):
    """Ours."""
    pass


assert 'Inputs\n------\nx : array' in from_google.__doc__
```

Give one format for all sources, or a mapping from a format to the sources
written in it.

Neither argument accepts an already-parsed {py:class}`~docshare.Document`: a
document was read when it was parsed and cannot be read again. This is
particular to these two arguments --- an ordinary inheritance source may be a
{py:class}`~docshare.Document`, as {doc}`inheriting` describes. Pass the
object it came from, or parse it the way you want it and pass that.

## The three format arguments

| Argument | What it is about |
| --- | --- |
| `format` | The format the decorated object's own docstring is written in. The default detects it. |
| `render` | The format the composed documentation is written out in. The default is `format`. |
| `sourceformat` | The format a *source* is written in. There is no default: a source's format is detected, so that inheriting across the two formats keeps working. |

## What a declaration cannot do

A rendered docstring does not carry its own declaration. After `docwrap`
writes an `Inputs` section, anything that reads that docstring afresh
without declaring `Inputs` sees an opaque section in NumPy style, or prose
in Google style. Within a session the cache hides this, because a composed
document is recorded under the plain key as well; it is a convenience and
not a guarantee. A function that inherits from a decorated one needs the
declaration too:

```python
@docwrap(
    custom={'Inputs': 'Parameters'},
    format='numpy',
    inheritinputs=refit,
    sourcecustom=True,
)
def refit_again(w, x):
    """Again."""
    pass


assert 'The observed data.' in refit_again.__doc__
```

A declared section also cannot be something neither format can express. A
title is written with letters, digits, spaces and hyphens and begins with a
letter, in both styles; `Model I/O` is refused rather than silently lost.
Nor can a declaration redefine a section `docshare` already recognizes.
