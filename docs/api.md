# API reference

```{eval-rst}
.. currentmodule:: docshare
```

Everything below is rendered from `docshare`'s own docstrings, which are
NumPy style --- the format this library reads.

## Composing

```{eval-rst}
.. autofunction:: docwrap
.. autofunction:: doccompose
.. autofunction:: docrender
```

## Reading

```{eval-rst}
.. autofunction:: docparse
.. autofunction:: docinfo
.. autofunction:: clear_docinfo
```

## The document model

```{eval-rst}
.. autoclass:: Document
   :members:

.. autoclass:: Section
   :members:

.. autoclass:: Item
   :members:

.. autoclass:: FrozenDict
   :members:
```

## Sections

```{eval-rst}
.. autoclass:: SectionKind
   :members:

.. autofunction:: section_kind

.. autodata:: SUPPORTED_FORMATS
```

## The cache

```{eval-rst}
.. autoclass:: DocCache
   :members:

.. autodata:: doccache
   :no-value:
```

## Exceptions

```{eval-rst}
.. autoexception:: DocShareError
.. autoexception:: DocParseError
.. autoexception:: DocFormatError
.. autoexception:: DocInheritanceError
.. autoexception:: DocMappingError
.. autoexception:: DocSignatureError
```
