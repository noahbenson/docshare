# Deferred edge cases

Cases deliberately left for after the enumerated implementation phases are
complete. Each entry records what the current behavior is, why it was
deferred, and what a fix would involve, so that revisiting one does not mean
rediscovering it.

Add to this file whenever an edge case is knowingly left unresolved.


## 1. Section-level prose in a structured section

*Raised in phase 2. Specification section 31.*

The specification asks that section descriptions be preserved. In a
structured section, `docshare` currently treats every line at column zero as
an item declaration, so prose that introduces the section becomes a phantom
item:

```text
Parameters
----------
All of these are optional.

x : int
    The x.
```

The first line parses as an item whose name is `All of these are optional.`.
`Section.text` is therefore always empty for a structured section; prose and
opaque sections are unaffected and keep their bodies verbatim.

The obstacle is that no non-heuristic rule separates such prose from a
parameter documented with neither a type nor a description, which is legal.
numpydoc has the same limitation. Candidate rules, none yet adopted:

* treat a leading block as prose when it is followed by a blank line and no
  line in it parses as a declaration with a type;
* treat a leading block as prose when its first line ends with sentence
  punctuation;
* require the author to disambiguate, and document that a structured section
  may not open with prose.

A fix touches `_numpy.parse_items`, `_google.parse_items`, and the renderer,
which would need to emit `Section.text` before the items.


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


## 10. `dropparams` and `dropreturns` name opposite sides

*Raised in phase 6. Specification sections 17 and 24.*

Section 17 says `dropparams` excludes *target* parameters from inheritance:
"do not supply inherited documentation for `foo`". Section 24 says
`dropreturns` specifies *source* return items that should not be inherited,
and its example confirms it: dropping `(0, 2)` from a source with four
returns inherits source returns 1 and 3.

These are opposite directions, and the implementation follows each literally:
a name-identified section drops target identities, an index-identified
section drops source identities. For names the two coincide unless `parammap`
is also in play, and for indices only the source side is meaningful, so the
inconsistency is invisible in every ordinary case.

It does surface when `parammap` and `dropparams` are combined: dropping the
target name is what excludes the parameter, not the source name it maps from.
Worth deciding deliberately when the specification is next revised.


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
