# Errors

`docshare` prefers an error to a guess. Every exception derives from
{py:exc}`~docshare.DocShareError`.

| Exception | Raised when |
|---|---|
| {py:exc}`~docshare.DocParseError` | A docstring cannot be read in the format required. |
| {py:exc}`~docshare.DocFormatError` | A format is unsupported, ambiguous, or missing. |
| {py:exc}`~docshare.DocInheritanceError` | The requested inheritance is incoherent. |
| {py:exc}`~docshare.DocMappingError` | A mapping or a bound source is invalid. |
| {py:exc}`~docshare.DocSignatureError` | Documentation describes a parameter the object lacks. |

Messages are meant to be actionable. Some examples:

A misspelled parameter:

```text
the documentation of f(x, y=1) describes a parameter 'scal' in its
'Parameters' section, but f has no such parameter. Correct the name, or, if
it is documented deliberately because it is taken from **kwargs, declare it
with extraparam='scal'
```

Half of a grouped declaration:

```text
the source documents 'x, y' as one grouped declaration, but only part of
that group can be inherited by partial: 'x' is already documented by partial
itself. A group is inherited whole or not at all, so either document every
name in it on partial, or document none of them and let the whole group be
inherited
```

The wrong exclusion argument:

```text
docwrap() got an unexpected argument 'dropreturns'; use ignorereturns=
instead. The Returns section is driven by its sources, which decide what
items exist, so an exclusion names one of the source's items. Excluding one
of the target's would do nothing, since the target's own documentation is
kept regardless.
```

An unrecognized argument suggests a close match:

```text
docwrap() got an unexpected argument 'inheritparam'; did you mean
'inheritparams' or 'inheritotherparams' or 'inheritwarns'?
```

## When errors are raised

Argument mistakes are caught before any work is done, so a failed decoration
never leaves a half-composed docstring behind. Signature validation runs
before composition and again on the composed result, so inheritance cannot
introduce a parameter the object does not have.
