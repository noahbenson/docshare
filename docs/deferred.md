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
