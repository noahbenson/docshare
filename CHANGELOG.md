# Changelog

All notable changes to `docshare` are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
follows [semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
