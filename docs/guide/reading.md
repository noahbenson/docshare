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

An object with no docstring, or one that is empty, is not an error: it parses
to an empty document, all of whose components are absent.

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

{py:data}`docshare.doccache` is an ordinary mutable mapping from a
`(format, custom, docstring)` triple to the {py:class}`~docshare.Document`
that triple parses to, bounded by `doccache.maxsize` and discarding its least
recently used entry when full.

It is keyed by the documentation rather than by the object, so two objects
documented alike share one record and a reassigned docstring simply misses.
That also means the cache never refers to the objects it describes: it cannot
keep one alive, and there is no object it cannot handle.

The format is part of the key because one text can be read two ways. A NumPy
declaration with an empty type has the shape of a Google section header, so a
`Parameters` section ending in `notes :` holds a parameter called `notes` in
one format and starts a `Notes` section in the other. Were the key the text
alone, whichever format was asked for first would answer every later request
as well --- including the correct one.

So `docinfo(f, format='numpy')` and `docinfo(f, format='google')` are
separate questions with separate answers, and asking one does not spoil the
other.

The declared sections are part of the key for the same reason: one text read
under two different declarations is two documents. See {doc}`custom`.

You may inspect, clear, resize or pre-load it:

```python
import docshare

docshare.doccache.maxsize = 8192
docshare.clear_docinfo()
```

A key is checked on every access, so a bare docstring used as one is an error
rather than an entry that is written and never read again. It is otherwise
the library's own working state: putting a document into it that does not
match its key will produce documentation that matches nothing.
