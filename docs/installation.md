# Installation

```console
$ pip install docshare
```

`docshare` requires Python 3.10 or later and has **no runtime dependencies**.

## From a checkout

```console
$ git clone https://github.com/noahbenson/docshare
$ cd docshare
$ pip install -e '.[dev]'
```

The `dev` extra installs everything needed to test the package and build this
site. Three narrower extras are available:

`test`
: `pytest`, coverage, and the two libraries whose real docstrings the test
  suite reads --- NumPy and `absl-py`. Tests that use them skip when they are
  absent, so the package can still be tested without them.

`docs`
: Sphinx, the Furo theme, and MyST for this site.

`dev`
: Both of the above, plus `ruff` and `build`.

## Checking a checkout

```console
$ pytest
$ ruff check . && ruff format --check .
$ make -C docs html
```
