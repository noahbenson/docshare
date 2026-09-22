# -*- coding: utf-8 -*-
################################################################################
# docs/conf.py
#
# Configuration for the docshare documentation site.

"""Sphinx configuration for the `docshare` documentation."""

import os
import pathlib
import sys

# Allow the documentation to be built from a checkout without installing the
# package first; an installed copy takes precedence.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'src'))

import docshare

project = 'docshare'
author = 'Noah C. Benson'
copyright = f'2026, {author}'
release = docshare.__version__
version = '.'.join(release.split('.')[:2])

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]

# The pages are written in Markdown, as the repository's other documents are.
source_suffix = {'.md': 'markdown', '.rst': 'restructuredtext'}
myst_enable_extensions = ['colon_fence', 'deflist', 'fieldlist']
myst_heading_anchors = 3

# docshare's own docstrings are NumPy style, which is what napoleon reads.
# The API reference below is therefore rendered from documentation that
# docshare itself composed.
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_rtype = False
# Render an Attributes section as fields on the class rather than as
# separate entries, which autodoc would then describe a second time.
napoleon_use_ivar = True

autodoc_member_order = 'bysource'
autodoc_typehints = 'none'
autodoc_default_options = {
    'members': True,
    'undoc-members': False,
    'show-inheritance': True,
}

# Resolving these needs the network. A build that cannot reach them, such as
# the one the test suite runs, sets DOCSHARE_DOCS_OFFLINE so that the missing
# inventories are not reported as warnings.
if os.environ.get('DOCSHARE_DOCS_OFFLINE'):
    intersphinx_mapping = {}
else:
    intersphinx_mapping = {
        'python': ('https://docs.python.org/3', None),
        'numpy': ('https://numpy.org/doc/stable', None),
    }

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'README.md']

html_theme = 'furo'
html_title = f'docshare {version}'
html_static_path = []
html_theme_options = {
    'source_repository': 'https://github.com/noahbenson/docshare/',
    'source_branch': 'main',
    'source_directory': 'docs/',
}

# The Makefile, the CI workflow, and the test suite all build with `-W`, so a
# broken reference fails the build rather than quietly producing a broken
# page. `nitpicky` stays off so that a reference to an object outside the
# library, which has no inventory to resolve against when the build is
# offline, is not reported at all.
nitpicky = False
