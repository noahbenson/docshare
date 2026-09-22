# Changelog

All notable changes to `docshare` are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
follows [semantic versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0]

### Added

* `doccompose` and `docrender` compose documentation without decorating
  anything. `doccompose` returns the composed `Document` and `docrender` the
  rendered docstring, both accepting every argument `docwrap` does, and any
  of a docstring, an object, or an already-parsed `Document` as the thing to
  work on. An object brings its signature, so the documentation is validated
  and its parameters ordered as for `docwrap`; a string or a `Document` has
  none, so validation is skipped and a parameter section is driven by its
  sources. Because they install nothing, both work on objects whose
  `__doc__` cannot be written, and neither writes to the cache.
* A documentation site, built with Sphinx and published to GitHub Pages. The
  README is now a summary that links to it.
* An inheritance source may be an already-parsed `Document`, as returned by
  `docparse` or `docinfo`, wherever an object is accepted. That is how a
  source is supplied whose format has to be stated rather than detected.
* Every example in the documentation is now self-contained and is executed by
  the test suite, so a page cannot demonstrate something that does not work.
* Sections beyond the ones `docshare` recognizes can be declared per call, with
  `custom=` on `docparse`, `docinfo` and `docwrap`. Each title either names the
  recognized section it resembles --- borrowing whether its body holds items,
  how they are identified, and the type that stands in for a missing one --- or
  stands alone, which recognizes the title as a section and leaves its body
  uninterpreted. A declared section is a section of its own, not another name
  for what it resembles: the two may appear in one document and mean different
  things, so it keeps its own title, is never merged, and is never checked
  against the signature.

  Nothing is registered. A declaration applies only to the call that makes it,
  so one library cannot change how another library's docstrings are read.

  `docwrap` addresses a declared section as `inheritcustom`, `ignorecustom` and
  `custommap`, which take a title and so work for any section, and --- when the
  title is a Python name --- by arguments generated from it exactly as for a
  recognized one, so that `Inputs` offers `inheritinputs`, `ignoreinputs` and
  `inputmap`. `sourcecustom` says which sources share the declaration, which
  `inheritall` needs since it names no section, and `sourceformat` says which
  format a source is written in. Together these remove the need to thread
  `docparse` results through the library.
* `inheritsummary` and `inheritdescription` inherit the text above the first
  section, which is not a section and so was not reachable before. `inheritall`
  implies both, so it now means all of a source's documentation rather than
  all of it below the first line. What the target documents for itself is kept,
  as everywhere else.

* Prose introducing a structured section is preserved rather than read as an
  item declaration. A section whose items are identified by name may open
  with a description of the section as a whole; it is kept on the section,
  rendered ahead of the items, and is never inherited.
* A guide page, `docs/guide/concepts`, now holds the design rationale, the
  consolidated core invariants, the goals and non-goals, and the dependency
  policy. The `docs/spec.md` design specification, which had fallen behind
  the implementation, has been retired into the guide and removed; every
  reference to it, in the source, the tests, and the other documents, now
  names the behavior directly.

### Fixed

* A Google-style section header is now recognized by its title rather than by
  its punctuation. Any line ending in a colon above an indented block was read
  as a section, so ordinary prose --- `The tuple has the following elements:`,
  `For example:` --- became a section named after the sentence. Google style
  defines a fixed set of section titles, as Napoleon does, and a block with any
  other title is prose. Such a document is no longer Google-formatted on that
  evidence alone, so `format='numpy'` no longer raises `DocFormatError` for it.

  The cost is that a Google document cannot spell a section `docshare` does not
  recognize; a NumPy underline can, and still does. The text of such a block is
  preserved and rendered back exactly either way, but under Google style it is
  prose rather than an opaque section, so `inheritother` cannot name it.

### Changed

* The documentation cache is keyed by a `(format, custom, docstring)` triple
  rather than a `(format, docstring)` pair, since one text read under two
  declarations is two documents.
* A docstring that opens with the documented object's own call signature, as
  NumPy's ufuncs do, no longer reads that line as the summary. It describes
  one object, so inheriting it would attach the wrong signature to something
  else; it is kept aside, written back out for the object it was read from,
  and never inherited.
* The decorator is named `docwrap`. The package is still `docshare`; the
  decorator wraps one object's documentation around another's, and the two
  no longer shadow each other on import.
* The documentation cache is safe to use from several threads. Looking an
  entry up also marks it as recently used, and discarding entries walks the
  whole cache, so neither was a single dictionary operation; two of the
  resulting races were reproducible even under the GIL. Iteration and the
  views built on it now work from a snapshot.
* The documentation cache is keyed by the documentation text rather than by
  the documented object. Two objects documented identically share one
  record, a reassigned docstring simply misses, and the cache never refers to
  the objects it describes, so every object can be cached. It is bounded and
  public as `docshare.doccache`, an ordinary mutable mapping whose `maxsize`
  can be changed.
* A Google-style section now ends where its indentation returns to column
  zero rather than at the next section header. Prose that follows a section
  is kept in place as a section with no title.
* The error reported when a document appears to mix both formats now explains
  the likeliest cause when one is present: a parameter declared with an empty
  type, such as `method :`, has the same shape as a Google section header.

### Fixed

* The documentation cache is keyed by `(format, docstring)` rather than by
  the docstring alone. One text can be read two ways --- a NumPy declaration
  with an empty type has the shape of a Google section header --- and keyed
  by text alone, whichever format was asked for first answered every later
  request as well, including the correct one.
* An item described without a type, which is how Google style writes a
  return value, a raised error, or a warning, is now written in NumPy with
  the least specific type of its hierarchy --- `object`, `Exception`, or
  `Warning` --- since the NumPy standard requires one. A declaration that
  gives no name and ends a sentence is read as a description rather than as
  a type, so prose no longer masquerades as one.
* A reStructuredText role used as a type, such as ``:class:`ndarray```, is no
  longer split at its leading colon.
* Binding a source to a *position* in a section whose items are identified by
  name, as in `inheritparams=(source, 0)`, is now rejected. It previously
  matched no item and, because a bound source takes no part in the ordinary
  search either, inherited nothing at all without saying so.

## [0.2.1]

### Added

* `docwrap` is annotated as an identity-preserving generic decorator, so a
  type checker sees through it to the annotated object it returns instead of
  treating the decorated function as `Any`. The annotations describe the
  behavior the decorator already had (it returns the object it was given);
  nothing about the decorator changes at run time. Libraries that decorate
  many of their own functions with `docwrap`--`immlib` decorates most of
  `immlib.math` with it--can now expose their own annotations to type
  checkers.

## [0.1.0]

First release.

### Added

* `docshare`, a decorator that composes an object's documentation from its
  own docstring and from sources named explicitly, and writes the result back
  to `__doc__` as ordinary documentation.
* `docparse`, which parses an object's current documentation into an
  immutable, format-independent `Document`.
* `docinfo`, which answers from a weakly-keyed cache, recording the composed
  document so that chains of inheritance work.
* NumPy and Google docstring parsing and rendering, with automatic format
  detection and a `render` argument for writing a document in the other
  format.
* Inheritance of every recognized section, with multiple sources resolved
  right to left, explicit binding of one item to one source, exclusion, and
  target-to-source item mapping. A section documenting the callable's
  parameters is ordered by the signature and excludes one of the target's own
  parameters with `drop<short>`; every other section is driven by its sources
  and excludes one of theirs with `ignore<short>`.
* Preservation of grouped declarations such as `x, y : float`, including
  renaming through `parammap`; partially inheriting a group is an error.
* Preservation of unrecognized sections, which are inherited only when named
  through `inheritother`.
* Signature validation at decoration time, with `extraparam` for parameters
  taken from `**kwargs`.
* Support for functions, methods, classes, properties, static methods, and
  class methods, in either decorator ordering.

### Notes

* No runtime dependencies.
* Requires Python 3.10 or later.

[0.3.0]: https://github.com/noahbenson/docshare/releases/tag/v0.3.0
[0.2.1]: https://github.com/noahbenson/docshare/releases/tag/v0.2.1
[0.1.0]: https://github.com/noahbenson/docshare/releases/tag/v0.1.0
