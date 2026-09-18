# Sections

`docshare` normalizes the two formats' section titles onto one set of kinds,
so a NumPy `Parameters` section and a Google `Args:` section are the same
thing internally.

## What each section offers

Every section accepts `inherit<short>`. Every section that holds items also
accepts a mapping and an exclusion; see {doc}`inheriting` for the difference
between `drop` and `ignore`.

| Section | Inherit | Exclude | Map |
|---|---|---|---|
| Parameters / Args | `inheritparams` | `dropparams` | `parammap` |
| Other Parameters | `inheritotherparams` | `dropotherparams` | `otherparammap` |
| Keyword Args | `inheritkeywordargs` | `dropkeywordargs` | `keywordargmap` |
| Returns | `inheritreturns` | `ignorereturns` | `returnmap` |
| Yields | `inherityields` | `ignoreyields` | `yieldmap` |
| Receives | `inheritreceives` | `ignorereceives` | `receivemap` |
| Raises | `inheritraises` | `ignoreraises` | `raisemap` |
| Warns | `inheritwarns` | `ignorewarns` | `warnmap` |
| Attributes | `inheritattributes` | `ignoreattributes` | `attributemap` |
| Methods | `inheritmethods` | `ignoremethods` | `methodmap` |
| Warnings | `inheritwarnings` | --- | --- |
| See Also | `inheritseealso` | --- | --- |
| Notes | `inheritnotes` | --- | --- |
| References | `inheritreferences` | --- | --- |
| Examples | `inheritexamples` | --- | --- |

The last five hold prose rather than items. They are inherited whole, and
only when you have no section of that kind; prose is never merged.

## Grouped declarations

A declaration may document several names at once:

```text
Parameters
----------
x, y : float
    Cartesian coordinates.
```

That is one documentation item, and it stays one. A group is inherited whole
or not at all: documenting only `x` yourself while inheriting the group is an
error, because the result would either contradict what you wrote or document
a parameter you do not have.

Renaming through `parammap` is fine so long as every member still
corresponds to one of your parameters. Renaming that would split a group is
the same error, and the message shows what the group would have become.

## Prose that introduces a section

A section whose items are identified by name may open with prose describing
the section as a whole:

```text
Parameters
----------
All of these are optional.

x : int
    The x.
```

That prose is kept on the section and written back ahead of the items. It is
never inherited: it describes the source's parameters, not yours.

A declaration either carries a type, which puts a colon on the line, or names
parameters, which are Python identifiers. Prose is neither. Only *leading*
prose is recognized, because text after the items is shaped exactly like a
description line that has lost its indentation.

## Sections `docshare` does not recognize

An unrecognized section is preserved exactly as written and never
interpreted:

```text
Efferents
---------
Connections to downstream objects.
```

Prose that follows a Google-style section belongs to neither the section nor
the next one, and is kept in place as a section with no title. It renders as
bare text and cannot be inherited, since there is no name by which to ask
for it.
