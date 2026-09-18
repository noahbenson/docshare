# Reading documentation

Two functions parse documentation without decorating anything.

```python
from docshare import docparse, docinfo
```

{py:func}`~docshare.docparse` parses an object's current documentation from
scratch and returns a {py:class}`~docshare.Document`: a summary, a
description, and an ordered sequence of sections, each holding items or text.
The representation is immutable and does not depend on which format it was
written in.

{py:func}`~docshare.docinfo` answers from a cache instead, parsing only when
it has nothing recorded. For an object `docwrap` has decorated, that record
is the *composed* document --- everything inheritance assembled, not just
what the original docstring said --- which is what makes chains of
inheritance work.

Both accept a docstring directly, which is convenient for experimenting:

```python
from docshare import docparse

doc = docparse('''Summary.

    Parameters
    ----------
    x : int
        The x.
    ''')
assert doc.section('parameters').items[0].names == ('x',)
```

A string is taken to *be* documentation rather than to have any; otherwise
this would parse the docstring of the {py:class}`str` type itself.

## The document model

{py:class}`~docshare.Document`, {py:class}`~docshare.Section` and
{py:class}`~docshare.Item` are frozen records.

* Sections are an ordered tuple, never a mapping, so document order survives.
  Lookup by kind or title is a convenience on top.
* A section whose title is not recognized is *opaque*: its body is preserved
  verbatim and never interpreted.
* An item may document several names at once, as in `x, y : float`. Such a
  group is kept intact rather than split.
* A documented type is retained as text and never interpreted as a Python
  type expression.

## The cache

{py:data}`docshare.doccache` is an ordinary mutable mapping from a docstring
to the {py:class}`~docshare.Document` it parses to, bounded by
`doccache.maxsize` and discarding its least recently used entry when full.

It is keyed by the documentation rather than by the object, so two objects
documented alike share one record and a reassigned docstring simply misses.
That also means the cache never refers to the objects it describes: it cannot
keep one alive, and there is no object it cannot handle.

You may inspect, clear, resize or pre-load it:

```python
import docshare

docshare.doccache.maxsize = 8192
docshare.clear_docinfo()
```

It is the library's own working state, so putting a document into it that
does not match its key will produce documentation that matches nothing.
