# Threads

`docshare` normally runs while a module is being imported, and two threads
may import two modules that each use it. That is safe.

The cache is the library's only shared mutable state, and every operation on
it is atomic with respect to other threads. Iteration, and the `keys`,
`values` and `items` views built on it, work from a snapshot, so one thread
may walk the cache while another writes to it.

Everything else is either built once when `docshare` is imported and only
read afterwards, such as the table of recognized sections, or belongs to the
caller: parsing, composing and rendering keep no state between calls.

## Why a lock is needed at all

Looking an entry up also marks it as recently used, and discarding entries
walks the whole cache, so neither is a single dictionary operation. Two of
the resulting races were reproducible even under the GIL:

```text
evict vs. resize     KeyError('dictionary is empty')
iterate vs. mutate   RuntimeError('OrderedDict mutated during iteration')
```

Free-threaded builds make them likelier rather than rarer.

## Parsing happens outside the lock

Two threads that ask for the same unrecorded docstring at once will both
parse it, and one will replace the other's entry. A parsed document depends
on nothing but the text it came from, so the two are equivalent. Holding the
lock across parsing would serialize exactly the work the cache exists to
avoid.

## What is not guaranteed

Anything about the objects you decorate. Two threads decorating the same
object at the same time race on its `__doc__` like any other attribute.
Normal use decorates each object once, while the module defining it is being
imported.
