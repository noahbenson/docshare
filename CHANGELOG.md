# Changelog

All notable changes to `docshare` are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
follows [semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* Prose introducing a structured section is preserved rather than read as an
  item declaration. A section whose items are identified by name may open
  with a description of the section as a whole; it is kept on the section,
  rendered ahead of the items, and is never inherited.

### Changed

* The decorator is named `docwrap`. The package is still `docshare`; the
  decorator wraps one object's documentation around another's, and the two
  no longer shadow each other on import.
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

[Unreleased]: https://github.com/noahbenson/docshare/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/noahbenson/docshare/releases/tag/v0.1.0
