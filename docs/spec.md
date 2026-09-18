# `docshare`

**Status:** Draft specification
**Version:** 0.1
**Language:** Python
**License:** MIT

## 1. Overview

> **Note.** This document is the specification `docshare` was built against.
> Where the implementation has since departed from it --- always
> deliberately, and always for a reason discovered while building or testing
> --- the departure is recorded in
> [`deferred.md`](deferred.md), and the current behavior is described in the
> [guide](guide/index). Section 8.1 has been revised in place; the decorator
> is named `docwrap` rather than `docshare`, and the exclusion arguments of
> sections 17, 24 and 42 are named `drop` or `ignore` according to which side
> they act on.

`docshare` is a lightweight Python library for parsing, composing, and selectively inheriting structured documentation from Python docstrings.

Its primary purpose is to eliminate repetitive documentation between related functions, methods, classes, and other documented Python objects while retaining ordinary Python docstrings as the final documentation source consumed by downstream tools.

For example:

```python
from docshare import docshare


@docshare(format='numpy')
def quuxatize(foo, bar=1):
    """A function that quuxizes the arguments `foo` and `bar`.

    Returns the quux of `foo` with `bar`: ``(foo*bar)**(foo + bar)``.

    Parameters
    ----------
    foo : float
        The foo parameter for the quux operation.
    bar : float, optional
        The bar parameter for the quux operation; the default is 1.

    Returns
    -------
    float
        The quux result.
    """
    return (foo * bar) ** (foo + bar)


@docshare(
    format='numpy',
    inheritparams=quuxatize,
)
def logquuxatize(foo, bar=1, base=None):
    """Returns the log of the quux of arguments `foo` and `bar`.

    Parameters
    ----------
    base : float, optional
        The base of the log that should be used; the default is ``None``.

    Returns
    -------
    float
        The log-quux result.
    """
    ...
```

The resulting `logquuxatize.__doc__` contains the documentation for `foo`
and `bar` inherited from `quuxatize`, followed by the explicitly documented
`base` parameter.

The fundamental principle is:

> **Inherited documentation fills gaps; it does not replace explicit
> documentation.**

`docshare` is intended to be a small, general-purpose utility rather than a
replacement for Sphinx, a documentation generator, or a complete semantic
model of Python programs.

---

# 2. Goals

`docshare` shall:

1. Provide reliable parsing of NumPy- and Google-style docstrings.
2. Provide composition and inheritance of documentation between Python
   objects.
3. Work with functions, methods, classes, properties, descriptors, and other
   documented Python objects where Python permits access to their
   documentation.
4. Preserve ordinary Python __doc__ strings as the final output.
5. Allow documentation to be inherited selectively by section and item.
6. Allow inherited parameters and other items to be renamed through explicit
   mappings.
7. Preserve documentation groups such as paired parameter declarations.
8. Preserve unknown documentation sections without requiring the library to
   understand them semantically.
9. Provide a parsed documentation representation through docparse.
10. Cache parsed documentation through docinfo.
11. Perform composition at decoration time.
12. Detect ambiguous or invalid composition and report useful errors.
13. Verify documented parameters against callable signatures by default, while
    allowing explicit exceptions for parameters that cannot be inferred from
    the signature.
14. Remain lightweight and pure Python.
15. Minimize dependencies.

---

# 3. Non-goals

`docshare` is not intended to:

* generate documentation;
* replace Sphinx or another documentation generator;
* replace Sphinx Napoleon;
* interpret Python type expressions semantically;
* validate whether a documented type is correct;
* execute documentation expressions;
* infer semantic equivalence between differently named parameters;
* dynamically update documentation after decoration;
* provide a general-purpose Python AST;
* fully understand arbitrary documentation markup;
* impose a particular documentation format on users.

The library should understand enough of NumPy and Google docstrings to
reliably compose them, but should not attempt to become a complete
documentation-processing framework.

---

# 4. Supported formats

The initial release shall support:

```python
'numpy'
'google'
```

The `format` argument shall be accepted wherever parsing or rendering format
semantics are required.

The default is:

```python
format=None
```

## 4.1 Explicit format

When a format is explicitly supplied, the document must conform to that
format.

For example:

```python
docparse(foo, format='numpy')
```

must parse `foo.__doc__` as a NumPy-style docstring.

An invalid document shall result in a `DocParseError` or another appropriate
`docshare` exception.

The library must not silently reinterpret an invalid document as another
format.

## 4.2 Automatic format detection

When:

```python
format=None
```

the library shall attempt to detect the format.

If the format can be identified unambiguously, parsing proceeds using that
format.

If it cannot be determined reliably, `docshare` shall raise an error rather
than making an arbitrary choice.

## 4.3 Format-independent document information

The semantic document representation returned by `docparse` and `docinfo`
shall not fundamentally depend on the source format.

For example, a NumPy:

```text
Parameters
----------
x : float
    The input.
```

and a Google:

```text
Args:
    x (float): The input.
```

should result in equivalent semantic documentation information.

Format-specific information that is necessary to reproduce the source
document shall nevertheless be retained internally where appropriate.

---

# 5. Public API

The initial public API shall include:

```python
from docshare import docshare
from docshare import docparse
from docshare import docinfo
```

The primary interfaces are:

```python
docshare(...)
docparse(obj, *, format=None)
docinfo(obj, *, format=None)
```

Additional helper functions and classes may be public if they are necessary
for practical use, but the above constitute the core API.

---

# 6. `docshare`

`docshare` is a decorator that parses the decorated object's documentation,
performs requested inheritance/composition, renders the resulting document,
and assigns it to the object's documentation.

Basic usage:

```python
@docshare(format='numpy')
def foo(...):
    """..."""
```

Inheritance:

```python
@docshare(
    format='numpy',
    inheritparams=other_function,
)
def foo(...):
    """..."""
```

Composition occurs **at decoration time**.

Once decoration has completed, `docshare` has no responsibility for subsequent
changes to `__doc__` on the source or target objects.

---

# 7. `docparse`

`docparse(obj, *, format=None)` parses the current documentation of `obj`
from scratch.

Conceptually:

```python
info = docparse(foo)
```

means:

> Read `foo.__doc__` now and construct its semantic documentation
> representation.

`docparse` shall not rely on previously cached information.

It shall:

1. obtain the object's current documentation;
2. determine the documentation format;
3. parse the document;
4. construct the semantic document representation;
5. return the resulting document.

## 7.1 Empty documentation

An object whose documentation is `None` or an empty string shall produce an
empty document.

For example:

```python
def foo():
    pass

info = docparse(foo)
```

shall return an empty document representation rather than raising an error.

---

# 8. `docinfo`

`docinfo(obj, *, format=None)` returns the documentation information currently
associated with an object by `docshare`.

If cached information does not already exist, `docinfo` shall parse the
object's current documentation using `docparse` and cache the result.

Thus:

```python
docinfo(foo)
```

is effectively a cached form of:

```python
docparse(foo)
```

## 8.1 Meaning of `format`

The `format` argument to `docinfo` applies only when the documentation must
actually be parsed.

`format` does not mean "return this document in the requested format". The
semantic document representation does not depend on the format a document was
written in, and `docinfo` never converts one document into another.

It does, however, depend on the format a document is *read as*, because a
single text can be read two ways. A NumPy declaration with an empty type has
the shape of a Google section header, so a `Parameters` section whose last
entry is `notes :` holds a parameter named `notes` when read as NumPy and
begins a `Notes` section when read as Google.

Cached information shall therefore be recorded against the format it was
parsed with, so that a request naming one format is never answered by a
document parsed as the other. Where two formats read a text identically, this
is invisible; where they do not, it is the difference between a correct
answer and a permanently wrong one.

An earlier draft of this specification required the opposite --- that cached
information be returned regardless of the format supplied --- on the grounds
that the representation is format-independent. That reasoning holds only once
the format is settled, and the requirement was dropped.

---

# 9. Internal caching

`docshare` shall maintain a package-level cache of parsed documentation.

The cache shall not require modifying the documented objects.

Where possible, the cache shall use weak references so that caching
documentation does not unnecessarily keep objects alive.

The implementation should use an appropriate weak-reference-based structure,
such as `weakref.WeakKeyDictionary`, where object types permit it.

Objects that cannot be weakly referenced may require a fallback mechanism.

## 9.1 Cache validity

Cached information represents the documentation at the time it was parsed.

The cache may retain the original documentation string or an equivalent
fingerprint so that changes to `__doc__` can be detected.

However, modification of `__doc__` after use of `docshare` is outside the
intended workflow.

The library does not need to dynamically propagate documentation changes.

---

# 10. Semantic document model

The internal representation shall distinguish at least:

* the document itself;
* summary/description text;
* sections;
* structured items within sections;
* item names;
* item types;
* item descriptions;
* item ordering;
* documentation groups.

A conceptual representation is:

```text
Document
├── summary
├── description
└── sections
    ├── Section
    │   ├── name
    │   ├── kind
    │   └── items
    │       ├── Item
    │       │   ├── names
    │       │   ├── type
    │       │   ├── description
    │       │   └── metadata
    │       └── ...
    └── ...
```

The exact Python representation may consist of immutable records rather than
nested dictionaries.

The representation must preserve enough information to reconstruct the
documentation without losing meaningful structure.

---

# 11. Immutability of parsed documentation

The objects returned by `docparse` and `docinfo` should preferably be
immutable.

This prevents accidental mutation of cached documentation information and
makes cached values safe to share.

Appropriate implementations include:

* frozen dataclasses;
* named tuples;
* immutable tuples and mappings;
* other lightweight immutable record types.

The exact representation is an implementation detail unless individual
record types become part of the public API.

---

# 12. Section ordering

Section ordering shall be preserved.

The document representation must not rely solely on a mapping such as:

```python
{
    'Parameters': ...,
    'Returns': ...,
}
```

because that loses information about the original order in some
representations and makes reconstruction unnecessarily difficult.

Sections shall therefore be represented as an ordered collection.

Lookup by section name may be provided as a convenience.

---

# 13. Structured and opaque sections

`docshare` shall distinguish between sections that it understands
semantically and sections that it does not.

For example, known sections may include:

* Parameters / Args
* Returns
* Yields
* Raises
* Attributes
* Methods
* Examples
* Notes
* Warnings
* See Also

The exact set of semantically understood sections depends on the supported
format.

Unknown sections must nevertheless be parsed sufficiently to preserve them.

For example:

```text
Efferents
---------
Connections from this object to downstream objects.
```

shall not cause an error merely because `Efferents` is unknown to `docshare`.

Unknown sections shall be preserved as opaque documentation.

---

# 14. Inheritance philosophy

Inheritance is explicitly requested by the user through the decorator.

The library shall not implicitly inherit arbitrary documentation merely
because two objects are related by Python inheritance or because one function
calls another.

For example:

```python
@docshare(inheritparams=foo)
def bar(...):
    ...
```

explicitly requests parameter inheritance from `foo`.

The fundamental inheritance rule is:

> **Inherited documentation fills gaps; it does not replace explicit
> documentation.**

If the target explicitly documents an item, that documentation takes
precedence over inherited documentation.

---

# 15. `inheritparams`

`inheritparams` specifies one or more sources from which parameter
documentation should be inherited.

For example:

```python
@docshare(
    format='numpy',
    inheritparams=quuxatize,
)
def logquuxatize(foo, bar=1, base=None):
    """..."""
```

The target receives documentation for matching parameters from
`quuxatize`, while retaining its own documentation for `base`.

## 15.1 Multiple sources

A sequence of sources may be supplied:

```python
inheritparams=(foo, bar, baz)
```

Inheritance uses a right-to-left precedence rule.

For a parameter occurring in multiple sources, the documentation is taken
from the **right-most source in which that parameter occurs**, unless the
target explicitly documents that parameter.

Thus:

```python
inheritparams=(foo, bar, baz)
```

means:

```text
baz > bar > foo
```

for inherited parameter documentation.

This is intentionally analogous to method-resolution-order semantics.

---

# 16. Explicit source-item selection

An inheritance source may be qualified to restrict inheritance to a specific
item.

For example:

```python
inheritparams=(
    foo,
    bar,
    baz,
    (foo, 'param1'),
)
```

means:

1. `param1` always inherits from `foo`;
2. all other parameters use `baz` if available;
3. otherwise `bar`;
4. otherwise `foo`.

The exact syntax for distinguishing a source object from a
`(source, item)` specification shall be unambiguous and shall be documented
as part of the public API.

---

# 17. `dropparams`

`dropparams` excludes target parameters from parameter inheritance.

Both a single parameter name and a sequence of names are accepted:

```python
dropparams='foo'
```

or:

```python
dropparams=('foo', 'bar')
```

Dropping affects inheritance only.

If a parameter is explicitly documented by the target, that documentation
remains.

Thus:

```python
dropparams='foo'
```

does not mean "remove `foo` from the target documentation."

It means:

> Do not supply inherited documentation for `foo`.

---

# 18. Parameter mapping

`parammap` establishes correspondence between target parameter names and
source parameter names.

The mapping direction is:

```text
target name -> source name
```

For example:

```python
parammap={'x': 'y'}
```

means:

> The target parameter `x` inherits documentation for source parameter `y`.

This permits inheritance when APIs use different parameter names for
conceptually equivalent arguments.

Exact name matching shall remain the default when no mapping is supplied.

Parameter mappings apply to inheritance only and do not rename the target's
actual Python parameters.

---

# 19. Extra parameters

Signature verification shall normally require documented parameters to
correspond to parameters in the callable's signature.

However, some APIs legitimately document parameters that are implicit in
`*args` or `**kwargs`.

The decorator shall therefore provide an `extraparam` option.

For example:

```python
@docshare(
    extraparam=('null',),
)
def foo(**kwargs):
    """...

    Parameters
    ----------
    null : bool
        ...
    """
```

declares `null` to be an intentional documented parameter even though it
does not appear as an explicit signature parameter.

A single name should also be accepted:

```python
extraparam='null'
```

`extraparam` applies to signature validation; it does not imply any runtime
behavior.

---

# 20. Signature validation

`docshare` shall use callable signatures to detect inconsistencies between
documented parameters and the callable interface.

Signature validation is intended to catch accidental documentation errors,
not to enforce a rigid relationship between documentation and signatures.

The validation system must account for:

* ordinary positional parameters;
* keyword parameters;
* keyword-only parameters;
* positional-only parameters;
* `*args`;
* `**kwargs`;
* explicitly declared extra parameters;
* parameter mappings.

Users shall have mechanisms to explicitly describe legitimate deviations
from the Python signature.

Signature validation should occur at decoration time.

---

# 21. Paired and grouped parameters

The parser must preserve parameter groups.

For example:

```text
Parameters
----------
x, y : float
    Cartesian coordinates.
```

is one documentation item whose names are:

```python
('x', 'y')
```

It must not automatically become two unrelated documentation items.

## 21.1 Inheriting a group

If the target inherits the group unchanged, the group shall remain unchanged.

## 21.2 Replacing the complete group

If the target independently documents both parameters, the inherited group
may be replaced by the two independent target items.

## 21.3 Partial replacement

If the source documents:

```text
x, y : float
    Cartesian coordinates.
```

and the target explicitly documents only:

```text
x : float
    Horizontal coordinate.
```

while attempting to inherit the source documentation, `docshare` shall
raise an error.

The error must explain that the source contains a grouped documentation item
and that the target has attempted to override only part of that group.

The user must either:

* document both `x` and `y`; or
* omit documentation for both so the source group can be inherited.

---

# 22. Generalized inheritance

Parameter inheritance is the first and most common use case, but the
underlying implementation shall support inheritance of arbitrary structured
sections.

The decorator shall provide dedicated convenience arguments for common
sections, including at least:

```python
inheritparams
inheritreturns
inheritraises
inherityields
inheritattributes
inheritexamples
inheritnotes
inheritwarnings
```

The implementation should normalize these options into a generalized
inheritance mechanism.

A generalized `inherit` interface may also be provided, for example:

```python
inherit={
    'Parameters': foo,
    'Returns': foo,
}
```

The dedicated options are convenience syntax for the corresponding
section-level operations.

---

# 23. Returns inheritance

`Returns` items may be named or unnamed.

For example:

```text
Returns
-------
result : float
    The result.
```

has a named return.

Where a return has no name:

```text
Returns
-------
float
    The result.
```

its identity is positional.

Return items therefore have at least two possible identifiers:

* name, when present;
* zero-based index.

For example:

```python
returnmap={0: 2}
```

means:

> Target return item 0 corresponds to source return item 2.

The mapping direction is always:

```text
target identity -> source identity
```

Named and positional identities may both be used where applicable.

---

# 24. `dropreturns`

`dropreturns` specifies source return items that should not be inherited.

For example:

```python
@docshare(
    inheritreturns=foo,
    dropreturns=(0, 2),
)
```

when `foo` has four return items inherits only source returns 1 and 3.

A single index should also be accepted:

```python
dropreturns=0
```

For named returns, names may be accepted as identities where appropriate.

---

# 25. Replacement of inherited returns

Because unnamed return items do not inherently identify their semantic role,
a target's explicit return documentation cannot always be inferred to
replace a particular source return item.

Explicit correspondence shall therefore be expressed using `returnmap`.

For example:

```python
@docshare(
    inheritreturns=foo,
    returnmap={0: 2},
)
def bar(...):
    """...

    Returns
    -------
    float
        Replacement documentation for source return 2.
    """
```

means that the target's return item 0 replaces source return item 2.

This mechanism shall be used whenever positional return correspondence
cannot be inferred unambiguously.

---

# 26. General item mappings

The same conceptual mechanism used by `parammap` and `returnmap` shall be
available for other structured sections where item identity is not always
obvious.

The mapping direction shall consistently be:

```text
target identity -> source identity
```

This provides a uniform mechanism for:

* renamed parameters;
* renamed returns;
* reordered return values;
* other named documentation items.

---

# 27. Explicit overrides

Target documentation always takes precedence over inherited documentation.

For example, if the source says:

```text
x : float
    Original description.
```

and the target says:

```text
x : float
    Replacement description.
```

the target description shall be retained.

The same principle applies to other structured sections.

Explicit target documentation is therefore the highest-precedence source.

---

# 28. Multiple inheritance precedence

For ordinary inherited items:

```python
inheritparams=(foo, bar, baz)
```

the effective precedence is:

```text
target documentation
        >
baz
        >
bar
        >
foo
```

A dropped item is excluded from inheritance.

An explicit mapping can establish a source item independently of the normal
source precedence.

For example:

```python
inheritparams=(
    foo,
    bar,
    baz,
    (foo, 'x'),
)
```

forces target `x` to use `foo.x`.

---

# 29. Arbitrary section inheritance

Unknown or format-specific sections shall be preserved but not inherited
automatically.

For example, if `foo` contains:

```text
Efferents
---------
Connections to downstream objects.
```

and `Efferents` is not a semantically recognized section, decorating another
function shall not cause that section to be inherited merely because
`foo` was supplied as an inheritance source.

The user may explicitly request it using:

```python
inheritother=[
    (foo, 'Efferents'),
]
```

This means:

> Inherit the `Efferents` section from `foo`.

`inheritother` shall preserve the complete section unless more specific
composition semantics are subsequently defined for that section.

This mechanism allows `docshare` to remain useful with domain-specific
documentation sections without requiring the parser to understand every
possible section name.

---

# 30. Preservation of opaque content

Text that `docshare` does not semantically understand shall be preserved.

This includes, for example:

* reStructuredText directives;
* Markdown;
* literal blocks;
* mathematical notation;
* hyperlinks;
* domain-specific markup;
* arbitrary prose.

The parser should identify structural boundaries without attempting to
interpret the content of descriptions unnecessarily.

---

# 31. Description and summary handling

The document model shall preserve:

* the initial summary;
* subsequent descriptive prose;
* section descriptions;
* item descriptions.

Unless explicitly requested by an inheritance operation, the target's
summary and description shall not be replaced by source documentation.

A future generalized composition interface may permit inheritance of these
components, but ordinary section inheritance must not implicitly replace
them.

---

# 32. Types

Types extracted from documentation shall be represented as text.

`docshare` shall not attempt to interpret expressions such as:

```text
array_like
Sequence[int]
tuple of float
str, optional
```

as Python types.

The library is concerned with documentation composition, not type checking.

---

# 33. Functions, methods, and classes

The library must support documentation attached to:

* ordinary functions;
* instance methods;
* static methods;
* class methods;
* properties;
* classes;
* callable objects where documentation can be accessed;
* descriptors where practical.

The implementation must not assume that every decorated object is an
ordinary function.

Decorator ordering with descriptors such as `classmethod`, `staticmethod`,
and `property` shall be tested explicitly.

Where Python's decorator mechanics make particular ordering necessary, that
requirement shall be documented.

---

# 34. Decorator interaction

`docshare` should work naturally with common decorators, especially
`functools.wraps`.

However, if a later decorator replaces an object's `__doc__`, the resulting
documentation is outside `docshare`'s control.

The library shall not attempt to dynamically track decorators or restore
documentation that another decorator subsequently replaces.

---

# 35. Documentation lifetime

Composition occurs at decoration time.

For example:

```python
@docshare(inheritparams=foo)
def bar(...):
    ...
```

captures the relevant documentation from `foo` when `bar` is decorated.

Subsequent changes to:

```python
foo.__doc__
```

do not modify `bar.__doc__`.

Similarly, modifying `bar.__doc__` after decoration is permitted by Python,
but is outside the intended operating model of `docshare`.

No dynamic dependency graph is required.

---

# 36. Empty target documents

A target may have no documentation:

```python
@docshare(inheritparams=foo)
def bar(...):
    pass
```

`docshare` shall be capable of constructing a document from inherited
sections even when the target starts with an empty docstring.

---

# 37. Section and item ordering

Inherited items shall be inserted into the target in a predictable order.

For a section such as `Parameters`:

1. explicitly documented target items retain their target ordering;
2. inherited items corresponding to target parameters are incorporated
   according to the target's parameter/signature ordering where possible;
3. additional inherited items that correspond to target parameters through
   explicit mappings follow the corresponding target positions;
4. inherited items that cannot be assigned a target position should result in
   a clear error rather than being placed arbitrarily.

The precise rendering algorithm shall be specified in the implementation
design, but ordering must be deterministic.

---

# 38. Signature and inheritance semantics

Inheritance does not require exact parameter-name equality.

For example:

```python
def foo(x, y):
    ...
```

and:

```python
def bar(a, b, scale):
    ...
```

may share documentation through:

```python
parammap={
    'a': 'x',
    'b': 'y',
}
```

Likewise, the target may inherit only a subset of the source parameters.

This is an essential use case for `docshare`.

The library should therefore think of inheritance as **documentation
correspondence**, not as copying an entire function signature.

---

# 39. Dependencies

`docshare` shall be a lightweight pure-Python package.

It shall have no runtime dependencies except those genuinely required to
understand and parse the supported documentation formats.

In particular, it should not depend on unrelated packages merely because
they are convenient.

Examples of dependencies that should not be introduced without necessity:

* NumPy;
* PyYAML;
* Sphinx;
* large general-purpose parser frameworks;
* type-checking frameworks.

If an actively maintained library provides a mature, authoritative parser
for one of the supported docstring formats, `docshare` may use that library
rather than unnecessarily implementing its own parser.

Otherwise, format parsing should be implemented internally.

Dependencies should be evaluated separately for the NumPy and Google
parsers if appropriate.

---

# 40. Error handling

`docshare` shall favor explicit errors over silent ambiguity.

Errors should be raised for cases such as:

* invalid documentation according to an explicitly requested format;
* ambiguous automatic format detection;
* incompatible inheritance;
* ambiguous target/source correspondence;
* partially overriding a grouped parameter;
* invalid mapping specifications;
* conflicting composition instructions;
* invalid signature/documentation relationships.

Errors should identify, where possible:

* target object;
* source object;
* section;
* affected item;
* relevant mapping;
* reason for the failure.

Error messages should be designed to tell the user how to correct the
documentation.

---

# 41. Recommended exception hierarchy

The implementation should provide a small exception hierarchy, for example:

```text
DocShareError
├── DocParseError
├── DocFormatError
├── DocInheritanceError
├── DocMappingError
└── DocSignatureError
```

The exact hierarchy may be adjusted during implementation.

All library-specific exceptions should derive from a common `DocShareError`
base class.

---

# 42. API consistency

Where an operation applies to a particular documentation section, the API
should use consistent terminology.

For example:

```python
inheritparams
parammap
dropparams

inheritreturns
returnmap
dropreturns

inheritraises
raisemap
dropraises
```

The underlying implementation should use a generalized section/item
mechanism rather than implementing each section independently.

---

# 43. Generalized `inherit` interface

The design should reserve a generalized inheritance interface such as:

```python
@docshare(
    inherit={
        'Parameters': foo,
        'Returns': foo,
    }
)
```

This may coexist with specialized convenience options:

```python
@docshare(
    inheritparams=foo,
    inheritreturns=foo,
)
```

The specialized options should be understood as syntactic sugar for the
general mechanism.

The generalized interface should support the same concepts:

* multiple sources;
* source-item selection;
* dropping items;
* mapping items;
* explicit target overrides.

---

# 44. `inheritall`

The API should support a convenience mechanism for inheriting all safely
inheritable documentation sections from a source.

Conceptually:

```python
@docshare(
    inheritall=foo,
)
```

This should not cause explicit target documentation to be overwritten.

Unknown opaque sections may be included only if `inheritall` explicitly
means all sections; ordinary section-specific inheritance must not implicitly
inherit unknown sections.

The exact treatment of opaque sections under `inheritall` shall be defined
consistently with the semantics of `inheritother`.

---

# 45. Format-specific section names

The semantic model should normalize equivalent format-specific section names.

For example, the NumPy:

```text
Parameters
----------
```

and Google:

```text
Args:
```

both represent the semantic "parameters" section.

Rendering should use the requested/document's format-specific section syntax.

---

# 46. Rendering

After composition, `docshare` shall render the semantic document back into
the selected documentation format.

Rendering must preserve:

* section ordering;
* item ordering;
* parameter groups;
* names;
* types;
* descriptions;
* opaque sections;
* meaningful indentation.

The resulting string shall be suitable for assignment to `__doc__`.

---

# 47. Round-trip expectations

For supported documents, parsing followed by rendering without semantic
modification should preserve the meaning and structure of the document.

Exact whitespace preservation is desirable but not necessarily required.

The library may normalize:

* indentation;
* blank lines;
* section spacing;
* equivalent formatting details.

It must not normalize away meaningful content.

---

# 48. Testing requirements

The test suite shall include at least:

## Basic parsing

* empty docstrings;
* summary-only documents;
* documents with descriptions;
* single sections;
* multiple sections;
* unknown sections.

## NumPy format

* parameters;
* grouped parameters;
* returns;
* named returns;
* unnamed returns;
* raises;
* yields;
* attributes;
* examples;
* notes;
* warnings;
* multiline descriptions.

## Google format

Equivalent coverage for Google syntax.

## Inheritance

* one source;
* multiple sources;
* right-most precedence;
* explicit target overrides;
* dropped items;
* mapped items;
* source-specific item selection;
* empty targets;
* partial inheritance.

## Grouped parameters

* unchanged groups;
* complete replacement;
* illegal partial replacement.

## Returns

* named returns;
* unnamed returns;
* positional mapping;
* dropping selected return items;
* reordering;
* explicit target replacement.

## Signatures

* ordinary parameters;
* positional-only parameters;
* keyword-only parameters;
* `*args`;
* `**kwargs`;
* `extraparam`;
* `parammap`.

## Python object types

* functions;
* instance methods;
* static methods;
* class methods;
* properties;
* classes.

## Caching

* `docinfo` after `docparse`;
* `docinfo` without prior parsing;
* weak-reference behavior;
* cache invalidation/fingerprint behavior where implemented.

---

# 49. Example: complete parameter inheritance

```python
@docshare(format='numpy')
def quuxatize(foo, bar=1):
    """Compute a quux.

    Parameters
    ----------
    foo : float
        The foo parameter.
    bar : float, optional
        The bar parameter; the default is 1.

    Returns
    -------
    float
        The quux.
    """
    ...


@docshare(
    format='numpy',
    inheritparams=quuxatize,
)
def logquuxatize(foo, bar=1, base=None):
    """Compute the logarithm of a quux.

    Parameters
    ----------
    base : float, optional
        The logarithm base; the default is ``None``.

    Returns
    -------
    float
        The logarithm of the quux.
    """
    ...
```

The resulting parameter section contains documentation for:

```text
foo
bar
base
```

with `foo` and `bar` inherited and `base` explicitly documented.

---

# 50. Example: selective inheritance

```python
@docshare(
    inheritparams=foo,
    dropparams=('internal',),
)
def bar(...):
    """..."""
```

The target inherits applicable parameters except `internal`.

---

# 51. Example: renamed parameter

```python
@docshare(
    inheritparams=foo,
    parammap={'input': 'x'},
)
def bar(input, scale=1):
    """..."""
```

The documentation for target parameter `input` is inherited from source
parameter `x`.

---

# 52. Example: multiple sources

```python
@docshare(
    inheritparams=(foo, bar, baz),
)
def quux(...):
    """..."""
```

For each parameter:

```text
target documentation
    > baz documentation
    > bar documentation
    > foo documentation
```

where the item is present in the relevant source.

---

# 53. Example: forced source precedence

```python
@docshare(
    inheritparams=(
        foo,
        bar,
        baz,
        (foo, 'special'),
    ),
)
def quux(...):
    """..."""
```

Target parameter `special` always inherits from `foo`.

All other parameters use right-most-source precedence.

---

# 54. Example: return mapping

Suppose `foo` has:

```text
Returns
-------
float
    First result.
float
    Second result.
float
    Third result.
float
    Fourth result.
```

A target may explicitly replace source return 3 with:

```python
@docshare(
    inheritreturns=foo,
    returnmap={0: 2},
)
def bar(...):
    """...

    Returns
    -------
    float
        Replacement description for the third result.
    """
```

Here target return 0 corresponds to source return 2.

---

# 55. Example: selective return inheritance

```python
@docshare(
    inheritreturns=foo,
    dropreturns=(0, 2),
)
def bar(...):
    """..."""
```

If `foo` has four return items, source returns 1 and 3 are inherited.

---

# 56. Example: arbitrary sections

```python
@docshare(
    inheritother=[
        (foo, 'Efferents'),
    ],
)
def bar(...):
    """..."""
```

The `Efferents` section is explicitly inherited even though `docshare` does
not have semantic knowledge of that section.

---

# 57. Compatibility with documentation ecosystems

The final decorated object's `__doc__` must contain ordinary documentation
text.

`docshare` must not require downstream tools to import `docshare` in order to
display or process documentation.

For example, after:

```python
@docshare(...)
def foo(...):
    ...
```

the following should operate on an ordinary completed docstring:

```python
help(foo)
```

Sphinx and its extensions should likewise be able to process the resulting
docstring normally.

---

# 58. Design philosophy

`docshare` should occupy a narrow layer between Python source code and
documentation tooling:

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

It should understand documentation structure without attempting to own the
entire documentation ecosystem.

---

# 59. Version 0.1 scope

The first release should implement:

* NumPy parsing;
* Google parsing;
* automatic format detection;
* semantic document representation;
* `docparse`;
* `docinfo`;
* weak-reference-based caching where possible;
* `docshare`;
* parameter inheritance;
* return inheritance;
* raises/yields/attributes inheritance;
* arbitrary-section preservation;
* `inheritother`;
* multiple inheritance sources;
* right-most inheritance precedence;
* explicit target overrides;
* `dropparams`;
* `dropreturns`;
* corresponding drop mechanisms for other supported structured sections;
* `parammap`;
* `returnmap`;
* corresponding mapping mechanisms for other supported structured sections;
* source-item selection;
* `extraparam`;
* signature validation;
* grouped parameter handling;
* functions, methods, classes, properties, static methods, and class methods;
* useful error reporting;
* generalized inheritance infrastructure;
* lightweight pure-Python packaging.

The first release should **not** attempt to implement:

* automatic semantic matching of differently named parameters;
* dynamic documentation updates;
* a full reStructuredText/Markdown parser;
* documentation generation;
* Sphinx integration beyond producing compatible `__doc__` strings;
* arbitrary Python type analysis.

---

# 60. Guiding example

The central use case can be summarized by:

```python
from docshare import docshare


@docshare(format='numpy')
def quuxatize(foo, bar=1):
    """A function that quuxizes the arguments `foo` and `bar`.

    Returns the quux of `foo` with `bar`: ``(foo*bar)**(foo + bar)``.

    Parameters
    ----------
    foo : float
        The foo parameter for the quux operation.
    bar : float, optional
        The bar parameter for the quux operation; the default is 1.

    Returns
    -------
    float
        The quux result.
    """
    return (foo * bar) ** (foo + bar)


@docshare(
    format='numpy',
    inheritparams=quuxatize,
)
def logquuxatize(foo, bar=1, base=None):
    """Returns the log of the quux of arguments `foo` and `bar`.

    Parameters
    ----------
    base : float, optional
        The base of the log that should be used; the default is ``None``.

    Returns
    -------
    float
        The log-quux result.
    """
    ...
```

The resulting documentation should behave as though the author had manually
written:

```text
Parameters
----------
foo : float
    The foo parameter for the quux operation.
bar : float, optional
    The bar parameter for the quux operation; the default is 1.
base : float, optional
    The base of the log that should be used; the default is ``None``.
```

The downstream documentation system should have no knowledge that `foo` and
`bar` were inherited.

---

# 61. Summary of core invariants

The implementation should preserve the following invariants:

1. **Explicit target documentation overrides inherited documentation.**
2. **Right-most inheritance sources have precedence.**
3. **Explicit mappings override ordinary name matching and source precedence.**
4. **Dropped items are excluded from inheritance but not removed from target
   documentation.**
5. **Grouped documentation remains grouped unless the target explicitly and
   completely replaces the group.**
6. **Partial replacement of a grouped parameter is an error.**
7. **Unnamed structured items may be addressed positionally.**
8. **Unknown sections are preserved but are not implicitly inherited.**
9. **Inheritance is explicit.**
10. **Composition occurs at decoration time.**
11. **The resulting `__doc__` is ordinary documentation text.**
12. **`docparse` parses from source; `docinfo` retrieves cached information.**
13. **The semantic document representation is independent of NumPy versus
    Google syntax.**
14. **Documentation inheritance does not require exact parameter-name
    equality.**
15. **Signature validation can be explicitly adjusted for legitimate
    documentation parameters not visible in the Python signature.**
16. **The library remains lightweight, pure Python, and minimally dependent.**

These invariants should guide implementation decisions whenever an edge case
is not explicitly covered elsewhere in the specification.
