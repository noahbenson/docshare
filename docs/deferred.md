# Deferred edge cases

Cases deliberately left for after the enumerated implementation phases are
complete. Each entry records what the current behavior is, why it was
deferred, and what a fix would involve, so that revisiting one does not mean
rediscovering it.

Add to this file whenever an edge case is knowingly left unresolved.


## 1. Section-level prose in a structured section --- RESOLVED

*Raised in phase 2; resolved after phase 8.*

A structured section may open with prose describing the section as a whole:

```text
Parameters
----------
All of these are optional.

x : int
    The x.
```

Every line at column zero used to be read as an item declaration, so the
first line became a parameter named after the sentence. In a Parameters
section that later produced a confusing signature error; in an Attributes
section, which has no signature to check against, it passed silently into the
rendered docstring.

The note filed here said no non-heuristic rule separated prose from a
parameter documented with neither a type nor a description. That was wrong:
the rule is syntactic. A declaration either carries a type, which puts a
colon on the line, or names parameters, which are Python identifiers
optionally starred. Prose is neither. `docshare._lex.is_declaration` applies
exactly that test, and `split_prose` takes the leading block that fails it.

Two boundaries make the rule safe:

* Only *leading* prose is recognized. Text after the items has the same shape
  as a description line that lost its indentation, and choosing between them
  would be the kind of guess the library avoids.
* Only a section whose items are identified by *name* can carry prose. In a
  section identified by position a line at column zero is a type, and a type
  is free text: `array_like of int` is a perfectly good NumPy return type and
  is indistinguishable from prose. Returns, Yields, Raises, and Warns
  therefore keep their previous reading, which also preserves the Google
  idiom of writing a return value as bare prose.

A single bare identifier alone on a line, such as `None`, still reads as a
declaration. That is ambiguous to a human reader too, and is left as it is.

Section prose is the target's own and is never inherited: it describes the
source's parameters, not the target's, for the same reason a summary stays
with the object that wrote it.

## 2. A parameter named after a section, declared with no type --- RESOLVED

*Raised in phase 2; resolved after phase 8.*

A NumPy declaration with an empty type has the same shape as a Google section
header: a title, a colon, and an indented body. Where the parameter's name is
also a recognized section title, detection cannot tell them apart and reports
the ambiguity.

The trigger is narrower than it first appears, and narrower than the section
count: it does not matter how many sections the document has, nor which ones.
What matters is the declaration form. `method : str` is unambiguous, and so
is a bare `method`; only a dangling colon, `method :` or `method:`, has the
shape of a header. Thirty-four recognized titles and aliases are affected,
including names people genuinely use --- `args`, `method`, `params`,
`attributes`, `returns`, `warnings`, `examples` --- but all of them only with
an empty type.

Resolved by documentation rather than by detection. The condition is already
an error, which is a stronger signal than the warning that was considered,
and three separate things resolve it: give the parameter a type, drop the
colon, or pass an explicit format. What was missing was that the message said
the document "mixes NumPy-style sections with Google-style sections
('method')", which is baffling when `method` is a parameter. The message now
explains that reading when the suspect header sits inside a NumPy section
rather than before one, and the README documents the case under formats.

## 3. A dashes line inside a prose section looks like a header --- ACCEPTED

*Raised in phase 2; accepted as-is after phase 8.*

A NumPy section header is a title underlined with at least three dashes, and
the title need not be one `docshare` recognizes --- an unknown section such
as `Efferents` must be preserved, so any plain line above a rule of dashes
opens a section. A prose section whose body
contains such a pair, as a hand-drawn table or a reStructuredText subsection
does, is therefore split in two:

```text
Notes
-----
Some background prose.

Background
----------
An RST subsection inside the notes.
```

Accepted rather than fixed, because the consequence is restructuring without
loss. The unrecognized title becomes an opaque section, whose body is
preserved verbatim and never interpreted, so every line survives. The example
above round-trips byte for byte; a hand-drawn table round-trips with one
blank line inserted, which is permitted. numpydoc treats an
unknown underlined title the same way.

Tightening the rule would mean either refusing unrecognized sections, which
the library forbids, or guessing from the title, which would be less
predictable than the present behavior. A docstring that genuinely needs a
dashes rule inside its prose can use a different underline character, which
reStructuredText allows and this rule ignores.

## 4. Cross-format rendering of keyword arguments is one-way --- ACCEPTED

*Raised in phase 1.*

Google's `Keyword Args:` has no NumPy equivalent, so it is merged into
`Parameters` when rendering NumPy. The distinction survives in the model and
in Google output, but a document rendered to NumPy and then re-parsed has
lost it, and cannot be rendered back to Google with the split restored.

This follows from the formats differing, not from a defect, and matches how
each format treats its own section names. It is recorded here only so that it
is not rediscovered as a bug.


## 5. A sectionless document has no format --- ACCEPTED

*Raised in phase 2.*

A document with no sections, such as a summary alone, parses with
`format=None` rather than raising, because it carries the same meaning in
both formats and so involves no arbitrary choice. A format becomes necessary
only when such a document must be rendered, which is where the requirement
for an explicit format applies.

Recorded as a deliberate choice rather than an omission.


## 6. An empty section is not written in Google format --- ACCEPTED

*Raised in phase 3; accepted as-is after phase 8.*

A Google section header is only a header when an indented body follows it, so
a section with no items and no text has no Google spelling. The renderer
keeps it in NumPy style, where a title and its underline stand alone, and
omits it in Google style.

Accepted rather than fixed. An empty section carries no documentation, so
nothing is lost by omitting it, and it does not reappear on a later
conversion back. The alternatives are worse: writing a placeholder body
invents content the author did not write, and refusing the conversion fails a
document that is otherwise perfectly convertible.


## 7. An item described without a type --- RESOLVED

*Raised in phase 3; resolved after phase 8.*

Google style permits a return value, a raised error, or a warning to be
described without naming its type. The NumPy standard does not: its
specification says of Returns that "the type of each return value is always
required", and repeats it for Yields. Napoleon tolerates the omission for
Raises and Warns but mangles it, putting the description where the exception
class belongs, which is the same failure this entry was about.

The first fix wrote the description on the declaration line, where a type
would go. That produced structurally invalid NumPy: numpydoc reads the
sentence as the item's *type*.

Resolved in two parts.

Reading: a declaration that gives no name is understood as a description
rather than a type when it ends a sentence. This is a heuristic, and
deliberately a narrow one, because no test decides the question from shape
alone --- English words are valid Python identifiers, and `The computed
result` is built exactly like `array_like of float`. A lexical test was tried
and rejected on the evidence: it called every prose example a type and also
rejected `Sequence[int]` and `tuple of (int, str)`. A type is a noun phrase
and never closes a sentence, so ending punctuation is the discriminator, and
anything not punctuated as prose keeps the meaning it always had. A type
written with a trailing full stop is misread; that is the price.

Writing: an item with a description and no type is written in NumPy with the
least specific type of its hierarchy --- `object` for a returned or yielded
value, `Exception` for a raised error, `Warning` for a warning --- which
asserts no more than the author did. Google style, which has no such
requirement, writes no type at all, so each format round-trips exactly within
itself.

A placeholder object in the model was considered for preserving the
cross-format round trip and does not achieve it: the model is not what
travels between formats, the text is, and a sentinel cannot survive being
written to a docstring. Full identity would additionally require reading
`object` back as "unspecified", which would silently rewrite a docstring that
named `object` deliberately. Converting therefore adds the type NumPy
requires and keeps it: a document that has made the round trip says
`object: The computed result.` in Google style. Nothing is lost, and
round-tripping was only ever required within a format.

Writing the tests for this uncovered an unrelated defect: a reStructuredText
role used as a type, such as ``:class:`numpy.ndarray```, was split at its
leading colon and lost its marker. A declaration with nothing before its
colon is no longer read as separating a name from a type.

## 8. Objects that cannot be weakly referenced --- RESOLVED

*Raised in phase 4; resolved after phase 8.*

The cache was keyed by the documented object and held its keys weakly, so an
object that could not be the target of a weak reference, and wrapped nothing
that could, was not cached at all. A write-only property was the one real
case; the three descriptor types that had to be handled were managed by
keying on the function each wraps.

Resolved by keying the cache on the documentation text instead of on the
object. A parsed document depends on nothing but the text it came from, so
the text is the honest key. The cache therefore never refers to the objects
it describes: it cannot keep one alive, and there is no object it cannot
handle, including a write-only property and an instance whose class defines
`__slots__` without `__weakref__`.

Caching must not keep objects alive or modify them. Both hold more simply
than before, and the weak-reference machinery --- the key resolution, the
descriptor unwrapping, the reference test --- is gone.

What the new key costs is that documentation strings cannot themselves be
weakly referenced, so entries are not reclaimed when their objects die. The
cache is therefore bounded, discarding the least recently used entry past
`docshare.doccache.maxsize`; losing one costs a reparse. The cache is public
as `docshare.doccache`, an ordinary mutable mapping, so it can be inspected,
cleared, resized, or pre-loaded.


## 9. A descriptor and its underlying function shared a key --- RESOLVED

*Raised in phase 4; resolved after phase 8.*

Because a `property` was keyed on its `fget`, a property built with an
overridden docstring shared a cache entry with the function itself while
having different documentation. Correctness was preserved by comparing the
recorded text on every lookup, but the two thrashed against each other.

Resolved by the same change. Keyed by documentation text, two objects share
an entry exactly when they are documented identically, which is when sharing
is correct; a property with its own docstring has its own entry. The separate
fingerprint comparison is gone, because the key is the fingerprint.

## 10. `dropparams` and `dropreturns` named opposite sides --- RESOLVED

*Raised in phase 6; resolved after phase 8.*

The original design made `dropparams` exclude a *target* parameter, while
`dropreturns` excluded a *source* return item. The two are opposite
directions, and neither is arbitrary: each names the only side that is both
available and useful.

A section documenting a callable's parameters is ordered by the signature.
The target says what exists and a source only fills it in, so the useful
exclusion names one of the target's own parameters; excluding a source
parameter would do nothing, because one the target does not have is never
inherited to begin with. Every other section is driven by its sources, which
decide what items exist --- there is no signature listing a function's return
values, and a target may document none at all --- so the only identities
available are the source's; and excluding a target item would do nothing
either, because the target's own documentation is kept regardless.

Resolved by naming the two differently rather than by unifying them. A
target-driven section offers `drop<short>` and no `ignore<short>`; a
source-driven section offers `ignore<short>` and no `drop<short>`. Using the
wrong one is an error that names the right one and says why:

```text
docwrap() got an unexpected argument 'dropreturns'; use ignorereturns=
instead. The Returns section is driven by its sources, which decide what
items exist, so an exclusion names one of the source's items. Excluding one
of the target's would do nothing, since the target's own documentation is
kept regardless.
```

Resolving this also uncovered two defects, both fixed at the same time. The
Other Parameters and Keyword Args sections document real parameters of the
callable but were not ordered by its signature, so inheriting one could
document a parameter the target did not have; they are now signature-ordered
like Parameters, and the composed document is validated before it is
installed, so nothing of the kind can reach `__doc__` unreported. And the
item mapping for a source-driven named section, such as `attributemap`, did
nothing at all, because the target contributed no candidate names for the
mapping to rename; a mapped name is now a candidate in its own right.

## 11. An integer bound to a name-identified section --- RESOLVED

*Raised in phase 6; resolved after phase 8.*

A source may be bound to one item with a `(source, key)` pair. In a section
whose items are identified by name the key must name one; a position
identifies nothing there. Such a binding used to match no item and say
nothing about it, and because a bound source takes no part in the ordinary
right-to-left search either, the source contributed nothing at all:
`inheritparams=(source, 0)` inherited an empty section in silence.

The form was easy to miss because writing the source twice hides it. In
`inheritparams=(source, (source, 0))` the plain source still contributes, so
the result looks correct while the binding is dead.

Resolved by rejecting it where the section kind is known, which covers both
the decorator and a direct call to `compose`:

```text
a source was bound to item 0 of the parameters section, but items there are
identified by name, so a binding must give one, as in (source, "x"). A
position identifies an item only in a section that is ordered by its source,
such as Returns or Raises
```

A position remains legal in a section ordered by its source, where both a
position and a label identify an item.

## 12. `format` cannot be used to convert a document --- RESOLVED

*Raised in phase 7; resolved in phase 8.*

The decorator's `format` argument says what the decorated docstring is
*written in*, and rendering originally used that same format, so a document
could not be asked to convert.

Resolved by adding a `render` argument that says what format the composed
documentation is written in, defaulting to `format`, or to the detected
format when `format` was not given. `format` therefore keeps its original
meaning, `render='numpy'` alone says how to write an object
that has no docstring to detect a format from, and giving both converts a
document from one format into the other.


## 13. The format is part of the cache key --- RESOLVED

*Raised after phase 8.*

The original design held that where cached information already exists,
`docinfo(foo, format='google')` returns it regardless of the format supplied,
on the grounds that the document representation is format-independent.

That holds for a text both formats read the same way, and fails for one they
do not. A NumPy declaration with an empty type has the shape of a Google
section header, so this docstring:

```text
S.

Parameters
----------
notes :
    Some notes.
```

is a Parameters section with a `notes` parameter when read as NumPy, and a
Notes section when read as Google. Under that rule whichever format was
asked for first answered every later request as well, so a single early call
with the wrong format left the object permanently misdescribed --- even to a
later call that named the format correctly.

The cache is therefore keyed by `(format, custom, documentation)` rather than
by documentation alone, and `docinfo` under two formats asks two questions. A
composed document is recorded under both the format it was written in and the
detecting request, since detecting the format of that text yields the same
answer.

The representation is format-independent only once the format is settled,
which is what the original rule overlooked.
