# -*- coding: utf-8 -*-
"""The shared documentation corpus used by the parser and renderer tests.

Each entry expresses the same documentation in both supported formats, so
that a single case can assert they agree, that each round-trips through the
renderer, and that either converts into the other.
"""

# Each entry is (id, numpy source, google source).
CORPUS = [
    (
        'summary-only',
        'Do a thing.',
        'Do a thing.',
    ),
    (
        'summary-and-description',
        'Do a thing.\n\nA longer explanation\nover two lines.\n',
        'Do a thing.\n\nA longer explanation\nover two lines.\n',
    ),
    (
        'parameters',
        'S.\n\n'
        'Parameters\n----------\n'
        'x : float\n    The x.\n'
        'flag : bool, optional\n    A flag; the default is False.\n',
        'S.\n\n'
        'Args:\n'
        '    x (float): The x.\n'
        '    flag (bool, optional): A flag; the default is False.\n',
    ),
    (
        'grouped-parameters',
        'S.\n\nParameters\n----------\nx, y : float\n    Coordinates.\n',
        'S.\n\nArgs:\n    x, y (float): Coordinates.\n',
    ),
    (
        'parameter-without-a-type',
        'S.\n\nParameters\n----------\nx\n    The x.\n',
        'S.\n\nArgs:\n    x: The x.\n',
    ),
    (
        'varargs-parameters',
        'S.\n\n'
        'Parameters\n----------\n'
        '*args : tuple\n    Positional extras.\n'
        '**kwargs : dict\n    Keyword extras.\n',
        'S.\n\n'
        'Args:\n'
        '    *args (tuple): Positional extras.\n'
        '    **kwargs (dict): Keyword extras.\n',
    ),
    (
        'unnamed-returns',
        'S.\n\nReturns\n-------\nfloat\n    The result.\n',
        'S.\n\nReturns:\n    float: The result.\n',
    ),
    (
        'named-returns',
        'S.\n\nReturns\n-------\nresult : float\n    The result.\n',
        'S.\n\nReturns:\n    result (float): The result.\n',
    ),
    (
        'several-unnamed-returns',
        'S.\n\nReturns\n-------\nfloat\n    First.\nint\n    Second.\n',
        'S.\n\nReturns:\n    float: First.\n    int: Second.\n',
    ),
    (
        'yields',
        'S.\n\nYields\n------\nint\n    Each value.\n',
        'S.\n\nYields:\n    int: Each value.\n',
    ),
    (
        'raises',
        'S.\n\n'
        'Raises\n------\n'
        'ValueError\n    If the input is bad.\n'
        'TypeError\n    If the type is wrong.\n',
        'S.\n\n'
        'Raises:\n'
        '    ValueError: If the input is bad.\n'
        '    TypeError: If the type is wrong.\n',
    ),
    (
        'warns',
        'S.\n\nWarns\n-----\nUserWarning\n    Sometimes.\n',
        'S.\n\nWarns:\n    UserWarning: Sometimes.\n',
    ),
    (
        'attributes',
        'S.\n\nAttributes\n----------\nvalue : int\n    The value.\n',
        'S.\n\nAttributes:\n    value (int): The value.\n',
    ),
    (
        'methods',
        'S.\n\nMethods\n-------\nrun : callable\n    Runs it.\n',
        'S.\n\nMethods:\n    run (callable): Runs it.\n',
    ),
    (
        'multiline-item-descriptions',
        'S.\n\n'
        'Parameters\n----------\n'
        'x : float\n    The x.\n'
        '    It has more to say\n    over three lines.\n',
        'S.\n\n'
        'Args:\n'
        '    x (float): The x.\n'
        '        It has more to say\n'
        '        over three lines.\n',
    ),
    (
        'several-sections',
        'S.\n\n'
        'Parameters\n----------\nx : int\n    The x.\n\n'
        'Returns\n-------\nint\n    The result.\n\n'
        'Notes\n-----\nA note.\n',
        'S.\n\n'
        'Args:\n    x (int): The x.\n\n'
        'Returns:\n    int: The result.\n\n'
        'Notes:\n    A note.\n',
    ),
    (
        'unknown-section',
        'S.\n\nEfferents\n---------\nDownstream connections.\n',
        'S.\n\nEfferents:\n    Downstream connections.\n',
    ),
]

CORPUS_IDS = [entry[0] for entry in CORPUS]


def semantics(doc):
    """Reduce a document to the parts that must not depend on its format."""
    return (
        doc.summary,
        doc.description,
        tuple(
            (section.kind, section.items, section.text)
            for section in doc.sections
        ),
    )
