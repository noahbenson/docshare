# Concepts and design

The rest of the guide describes how to make `docshare` do things. This page
describes what it is for and what it deliberately does not do, and collects
the rules that hold everywhere else in the documentation.

## Where `docshare` sits

`docshare` occupies one narrow layer between Python source code and the tools
that consume documentation. It reads `__doc__`, composes it, and writes it
back as ordinary text --- it does not replace anything downstream:

```text
Python objects
      │
      │ __doc__
      ▼
  docshare
      │
      ├── parse
      ├── identify
      ├── inherit
      ├── compose
      └── render
      │
      ▼
ordinary __doc__
      │
      ├── help()
      ├── IDEs
      ├── Sphinx
      └── documentation generators
```

The point of returning ordinary documentation is that nothing downstream
needs to know `docshare` was involved. `help()`, an editor, Sphinx, and
{py:mod}`inspect` all see a docstring an author might have written by hand. See
{ref}`sections docshare does not recognize <unrecognized-sections>` for how
that shapes what a `docshare` docstring may contain.

## Goals

`docshare` aims to:

* parse NumPy- and Google-style docstrings reliably, and detect which one a
  docstring uses;
* compose and inherit documentation between objects that would otherwise
  repeat it;
* work with functions, methods, classes, properties, static methods, and
  class methods;
* preserve ordinary `__doc__` strings as the final output;
* let documentation be inherited selectively, by section and by item, with
  renaming, exclusion, and per-item binding;
* keep grouped declarations such as `x, y : float` intact;
* preserve sections it does not understand rather than discarding them;
* expose the parsed representation through {py:func}`~docshare.docparse` and
  the cached one through {py:func}`~docshare.docinfo`;
* compose at decoration time, detect ambiguous or invalid composition, and
  report an actionable error;
* check documented parameters against the callable's signature, while
  allowing explicit exceptions for parameters taken from `**kwargs`;
* stay lightweight, pure Python, and without runtime dependencies.

## Non-goals

`docshare` is not a documentation generator, and does not try to be one. It
does not replace Sphinx or its Napoleon extension, and it does not own the
documentation ecosystem. In particular it does not:

* generate documentation;
* interpret a documented type as a Python type expression, or check that a
  type is correct;
* execute anything found in a docstring;
* infer that two differently named parameters mean the same thing;
* update documentation after decoration;
* parse arbitrary Python or arbitrary documentation markup;
* impose a documentation format on a caller.

It understands enough of NumPy and Google docstrings to compose them
faithfully --- no more and no less.

## The core invariants

These hold everywhere, and they are what to reach for when a case is not
otherwise covered. Each links to the page that develops it.

1. **Explicit target documentation overrides inherited documentation.** This
   is the one rule; see {doc}`inheriting`.
2. **Right-most inheritance sources have precedence.** See
   {doc}`inheriting`.
3. **Explicit mappings override ordinary name matching and source
   precedence.** See {doc}`inheriting`.
4. **Excluded items are left out of inheritance but not removed from the
   target's own documentation.** The two exclusion arguments act on opposite
   sides; see {doc}`inheriting`.
5. **Grouped documentation stays grouped unless the target explicitly and
   completely replaces the group.** See {doc}`sections`.
6. **Partial replacement of a grouped parameter is an error.** See
   {doc}`errors`.
7. **Unnamed structured items may be addressed by position.** See
   {doc}`inheriting`.
8. **Unknown sections are preserved but are not implicitly inherited.** See
   {doc}`sections`.
9. **Inheritance is always explicit** --- never inferred from a class
   hierarchy or a call graph.
10. **Composition happens at decoration time**, once, and is not recomputed.
11. **The resulting `__doc__` is ordinary documentation text.**
12. **{py:func}`~docshare.docparse` parses from source;**
    **{py:func}`~docshare.docinfo` retrieves cached information.** See
    {doc}`reading`. Composition does not require an object either:
    {py:func}`~docshare.doccompose` returns the composed document and
    {py:func}`~docshare.docrender` the rendered text. See {doc}`standalone`.
13. **The document model is independent of NumPy versus Google syntax.** See
    {doc}`formats`.
14. **Inheriting an item does not require its target and source names to
    match** --- a mapping says how they correspond.
15. **Signature validation can be adjusted** for a parameter documented
    deliberately but absent from the signature. See {doc}`signatures`.
16. **The library remains lightweight, pure Python, and without runtime
    dependencies.**
17. **Sections declared beyond the recognized ones apply only to the request
    that declares them.** See {doc}`custom`.

## Dependencies

`docshare` is a lightweight pure-Python package with no runtime dependencies.
The parsers for both formats are implemented internally, because every
third-party docstring parser evaluated discards the unknown sections and
grouped declarations that invariant 8 and invariant 5 require be preserved.
A dependency is therefore added only when it is genuinely needed to
understand a supported format, not because it is convenient.
