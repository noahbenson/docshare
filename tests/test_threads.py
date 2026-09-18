# -*- coding: utf-8 -*-
"""Tests that the documentation cache is safe to share between threads.

`docshare` runs while a module is being imported, and two threads may import
two modules that each use it. The cache is the library's only shared mutable
state; everything else is built once at import and read thereafter, or
belongs to the caller.

The stress tests here are probabilistic in one direction only. An
unsynchronized cache does not fail them on every run, but a synchronized one
cannot fail them at all, so a failure means a real defect rather than a flake.
"""

import contextlib
import sys
import threading

import pytest

from docshare import DocCache, Document, clear_docinfo, doccache, docinfo


@pytest.fixture
def interleaved():
    """Make thread switching as frequent as the interpreter allows."""
    original = sys.getswitchinterval()
    sys.setswitchinterval(1e-9)
    yield
    sys.setswitchinterval(original)


@pytest.fixture(autouse=True)
def _empty_cache():
    size = doccache.maxsize
    clear_docinfo()
    yield
    clear_docinfo()
    doccache.maxsize = size


def race(*targets):
    """Run the callables in parallel and return whatever they raised."""
    failures = []

    def guard(function):
        def wrapped():
            try:
                function()
            except BaseException as error:
                failures.append(f'{type(error).__name__}: {error}')

        return wrapped

    threads = [threading.Thread(target=guard(f)) for f in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return failures


def document(label='x'):
    """Return a small document to put in a cache."""
    return Document(summary=f'{label}.')


# The races that were reproducible before the cache was synchronized ########


def test_discarding_entries_while_the_bound_changes(interleaved):
    cache = DocCache(maxsize=50)

    def fill():
        for index in range(8000):
            cache[(None, None, f'k{index}')] = document()

    def resize():
        for index in range(8000):
            cache.maxsize = index % 5

    assert race(fill, fill, resize, resize) == []


def test_iterating_while_another_thread_writes(interleaved):
    cache = DocCache(maxsize=1000)

    def walk():
        for _ in range(1500):
            list(cache)

    def fill():
        for index in range(8000):
            cache[(None, None, f'k{index}')] = document()

    assert race(walk, fill) == []


def test_reading_a_snapshot_while_another_thread_writes(interleaved):
    cache = DocCache(maxsize=1000)

    def read():
        for _ in range(1500):
            len(cache.values())
            len(cache.items())
            len(cache.keys())

    def fill():
        for index in range(8000):
            cache[(None, None, f'k{index}')] = document()

    assert race(read, fill) == []


def test_reading_an_entry_while_another_thread_removes_it(interleaved):
    cache = DocCache(maxsize=100)
    cache[(None, None, 'k')] = document()

    def read():
        for _ in range(8000):
            with contextlib.suppress(KeyError):
                cache[(None, None, 'k')]

    def churn():
        for _ in range(8000):
            cache[(None, None, 'k')] = document()
            with contextlib.suppress(KeyError):
                del cache[(None, None, 'k')]

    assert race(read, read, churn) == []


def test_membership_while_another_thread_writes(interleaved):
    cache = DocCache(maxsize=200)

    def check():
        for index in range(8000):
            (None, None, f'k{index}') in cache  # noqa: B015 - the lookup is the point

    def fill():
        for index in range(8000):
            cache[(None, None, f'k{index}')] = document()

    assert race(check, fill) == []


def test_clearing_while_another_thread_writes(interleaved):
    cache = DocCache(maxsize=500)

    def fill():
        for index in range(8000):
            cache[(None, None, f'k{index}')] = document()

    def wipe():
        for _ in range(1500):
            cache.clear()

    assert race(fill, wipe) == []


def test_reporting_while_another_thread_writes(interleaved):
    cache = DocCache(maxsize=200)

    def report():
        for _ in range(3000):
            repr(cache)
            len(cache)

    def fill():
        for index in range(8000):
            cache[(None, None, f'k{index}')] = document()

    assert race(report, fill) == []


# The library's own entry points ############################################


def test_two_threads_documenting_different_things(interleaved):
    # Two modules being imported at once, each using docshare.
    def load(seed):
        def work():
            for index in range(1200):
                docinfo(
                    f'Summary {seed}-{index}.\n\n'
                    f'Parameters\n----------\n'
                    f'x{index} : int\n    The x.\n'
                )

        return work

    doccache.maxsize = 64
    assert race(*[load(seed) for seed in range(6)]) == []


def test_two_threads_documenting_the_same_thing(interleaved):
    text = 'S.\n\nParameters\n----------\nx : int\n    The x.\n'
    results = []

    def work():
        for _ in range(1200):
            results.append(docinfo(text))

    assert race(work, work, work) == []
    # Both threads may parse it, but every result says the same thing.
    assert all(d == results[0] for d in results)


def test_the_bound_is_respected_under_contention(interleaved):
    cache = DocCache(maxsize=8)

    def fill(seed):
        def work():
            for index in range(3000):
                cache[(None, None, f'{seed}-{index}')] = document()

        return work

    assert race(*[fill(seed) for seed in range(4)]) == []
    assert len(cache) <= 8


def test_parsing_shares_nothing_between_threads(interleaved):
    from docshare import docparse

    text = 'S.\n\nParameters\n----------\nx : int\n    The x.\n'
    results = []

    def work():
        for _ in range(1000):
            results.append(docparse(text))

    assert race(work, work, work) == []
    assert all(d == results[0] for d in results)


def test_composing_in_two_threads_at_once(interleaved):
    from docshare import docwrap

    def base(x):
        """B.

        Parameters
        ----------
        x : int
            The x from base.
        """

    results = []

    def work(seed):
        def run():
            for index in range(200):

                def target(x):
                    pass

                target.__doc__ = f'T{seed}-{index}.'
                docwrap(target, format='numpy', inheritparams=base)
                results.append(target.__doc__)

        return run

    assert race(*[work(seed) for seed in range(4)]) == []
    assert all('The x from base.' in doc for doc in results)


# The rest of the library holds no shared mutable state ######################


def test_the_section_registry_is_read_only():
    from docshare import section_kind

    kind = section_kind('parameters')
    with pytest.raises(Exception):  # noqa: B017 - FrozenInstanceError
        kind.name = 'other'
    with pytest.raises(TypeError):
        kind.titles['numpy'] = 'Other'
