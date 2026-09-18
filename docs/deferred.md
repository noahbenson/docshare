# Deferred edge cases

Cases deliberately left for after the enumerated implementation phases are
complete. Each entry records what the current behavior is, why it was
deferred, and what a fix would involve, so that revisiting one does not mean
rediscovering it.

Add to this file whenever an edge case is knowingly left unresolved.


## 1. Section-level prose in a structured section --- RESOLVED

*Raised in phase 2; resolved after phase 8. Specification section 31.*

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
source's parameters, not the target's, for the same reason section 31 keeps a
summary with the object that wrote it.

## 2. A parameter named after a section, declared with no type

*Raised in phase 2. Specification sections 4.2 and 40.*

A NumPy declaration with an empty type has the same shape as a Google section
header: a title, a colon, and an indented body. Context resolves this in
almost every case, but not when the parameter's name is also a recognized
section title:

```text
Parameters
----------
notes :
    Some notes.
```

Automatic detection reports an ambiguity here and directs the caller to pass
an explicit format. Passing `format='numpy'` reads the document as NumPy
alone and parses it correctly, so there is a supported way out; the residual
question is only whether the automatic case should somehow succeed.

A fix would need a rule that distinguishes the two without reference to the
title, such as requiring a Google header's body to parse as items of that
section. That is a larger change to the lexer than the case justifies.


## 3. A dashes line inside a prose section can look like a header

*Raised in phase 2. Specification section 30.*

A NumPy section header is a title underlined with at least three dashes. A
prose section whose body happens to contain a line of three or more dashes
directly beneath a short line of text, such as a hand-drawn table or a
horizontal rule, is read as a new section:

```text
Notes
-----
Column
------
```

No case of this has appeared in practice, and tightening the rule risks
rejecting legitimate short section titles. Revisit if it is encountered.


## 4. Cross-format rendering of keyword arguments is one-way

*Raised in phase 1.*

Google's `Keyword Args:` has no NumPy equivalent, so it is merged into
`Parameters` when rendering NumPy. The distinction survives in the model and
in Google output, but a document rendered to NumPy and then re-parsed has
lost it, and cannot be rendered back to Google with the split restored.

This follows from the formats differing, not from a defect, and matches how
the specification treats format-specific section names in section 45. It is
recorded here only so that it is not rediscovered as a bug.


## 5. A sectionless document has no format

*Raised in phase 2. Specification sections 4.2 and 7.1.*

A document with no sections, such as a summary alone, parses with
`format=None` rather than raising, because it carries the same meaning in
both formats and so involves no arbitrary choice. A format becomes necessary
only when such a document must be rendered, which is where the requirement
for an explicit format applies.

Recorded as a deliberate reading of section 4.2 rather than an omission.


## 6. An empty section cannot be written in Google format

*Raised in phase 3. Specification section 46.*

A Google section header is only a header when an indented body follows it, so
a section with no items and no text has no Google spelling. The renderer
therefore drops such a section when writing Google style, while NumPy style
keeps it, since a title and its underline stand alone perfectly well.

An empty section carries no documentation, so nothing is lost in practice.
The alternative, writing a placeholder body, would invent content. Revisit
only if an empty section turns out to matter.


## 7. A return described without a type has no NumPy spelling

*Raised in phase 3. Specification sections 46 and 47.*

Google style permits a return value written as bare prose::

    Returns:
        The computed result.

This parses as an item with neither a name nor a type, only a description.
NumPy style has no such form: every entry in a Returns section begins with a
type or a name. The renderer therefore promotes the first line of the
description onto the declaration line, so that the NumPy output is valid and
says the same thing to a reader:

```text
Returns
-------
The computed result.
```

Parsing that back yields an item whose *type* is `The computed result.`, so
the conversion is not semantically reversible. Within a single format the
round trip is exact; only the cross-format conversion shifts the text from
description to type.

A fix would require either inventing a type such as `object`, which asserts
something the author did not write, or leaving the description off entirely,
which loses it. Neither is clearly better than the current behavior.


## 8. Objects that cannot be weakly referenced are not cached

*Raised in phase 4. Specification section 9.*

The specification allows a fallback for objects that cannot be the target of
a weak reference. The fallback chosen is to parse such an object's
documentation afresh on every call rather than to record it, since the
alternatives --- keying on `id`, which is reused after collection, or holding
a strong reference, which leaks --- are each worse than losing an
optimization.

The three descriptor types the specification requires support for, produced
by `staticmethod`, `classmethod`, and `property`, cannot themselves be weakly
referenced, but each wraps a function that can be, and the cache keys on that
function instead. So the uncached case is confined to objects that both
resist weak reference and wrap nothing, such as a write-only property or an
`int`. Correctness is unaffected; only the caching is.

One consequence: a composed document recorded for such an object cannot be
recorded at all, so `docinfo` would reparse its rendered docstring. Where
rendering is lossy, as in case 7 above, the reparsed document could differ
from the composed one. No object of this kind is a plausible decoration
target, but the interaction is worth remembering.


## 9. A descriptor and its underlying function share a cache key

*Raised in phase 4.*

Because a `property` keys on its `fget`, a property built with an overridden
docstring, as in `property(f, doc='Something else.')`, shares a cache key
with `f` itself while having different documentation. The same holds for a
`staticmethod` wrapping a function that is also documented in its own right.

Correctness is preserved by the fingerprint: an entry is used only while the
recorded text still matches the object's current `__doc__`, so a lookup that
collides simply reparses. The only cost is that alternating lookups between
the two objects would reparse every time instead of hitting the cache.

A fix would require a composite key, which a `WeakKeyDictionary` cannot hold
directly. Revisit only if the pattern turns out to be common.


## 10. `dropparams` and `dropreturns` named opposite sides --- RESOLVED

*Raised in phase 6; resolved after phase 8.*

Section 17 made `dropparams` exclude a *target* parameter, while section 24
made `dropreturns` exclude a *source* return item. The two are opposite
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
docshare() got an unexpected argument 'dropreturns'; use ignorereturns=
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

## 11. An integer bound to a name-identified section is ignored

*Raised in phase 6. Specification section 16.*

A source may be bound to one item with a `(source, key)` pair. In a
name-identified section the key is a name, and in an index-identified section
it may be a name or a position. A position given for a name-identified
section, as in `inheritparams=(foo, (foo, 0))`, matches nothing and is
silently ignored rather than reported.

Detecting it requires knowing the section kind while normalizing the
decorator's arguments, which is where it should be caught. Worth doing when
the decorator's argument validation is revisited.


## 12. `format` cannot be used to convert a document --- RESOLVED

*Raised in phase 7; resolved in phase 8.*

The decorator's `format` argument says what the decorated docstring is
*written in*, per specification section 4.1, and rendering originally used
that same format, so a document could not be asked to convert.

Resolved by adding a `render` argument that says what format the composed
documentation is written in, defaulting to `format`, or to the detected
format when `format` was not given. `format` therefore keeps its
specification meaning, `render='numpy'` alone says how to write an object
that has no docstring to detect a format from, and giving both converts a
document from one format into the other.
