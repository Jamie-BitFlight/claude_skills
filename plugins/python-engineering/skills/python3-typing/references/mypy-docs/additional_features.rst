Additional features
-------------------

.. _dataclasses_support:

Dataclasses
***********

:py:mod:`dataclasses` module provides :py:func:`@dataclasses.dataclass <dataclasses.dataclass>` decorator for boilerplate-free classes:

.. code-block:: python

    from dataclasses import dataclass, field

    @dataclass
    class Application:
        name: str
        plugins: list[str] = field(default_factory=list)

    test = Application("Testing...")  # OK
    bad = Application("Testing...", "with plugin")  # Error: list[str] expected

Mypy detects special methods based on flags:

.. code-block:: python

    @dataclass(order=True)
    class OrderedPoint:
        x: int
        y: int

    @dataclass(order=False)
    class UnorderedPoint:
        x: int
        y: int

    OrderedPoint(1, 2) < OrderedPoint(3, 4)  # OK
    UnorderedPoint(1, 2) < UnorderedPoint(3, 4)  # Error: Unsupported operand types

Dataclasses can be generic (Python 3.12+):

.. code-block:: python

    @dataclass
    class BoxedData[T]:
        data: T
        label: str

    def unbox[T](bd: BoxedData[T]) -> T:
        ...

    val = unbox(BoxedData(42, "<important>"))  # OK, inferred type is int

Caveats:

- Functions like :py:func:`~dataclasses.asdict` have imprecise types
- Mypy doesn't recognize aliases of :py:func:`~dataclasses.dataclass` or dynamically computed decorators
- Use :py:func:`~typing.dataclass_transform` for wrapper recognition:

.. code-block:: python

    from dataclasses import dataclass, Field
    from typing import dataclass_transform

    @dataclass_transform(field_specifiers=(Field,))
    def my_dataclass[T](cls: type[T]) -> type[T]:
        return dataclass(cls)

Data Class Transforms
*********************

Mypy supports :py:func:`~typing.dataclass_transform` (PEP 681).

Note: Mypy assumes such classes have ``__dataclass_fields__`` attribute and treats them as dataclasses for :py:func:`~dataclasses.is_dataclass` and :py:func:`~dataclasses.fields` (may differ from runtime).

.. _attrs_package:

The attrs package
*****************

:doc:`attrs <attrs:index>` package supported. Mypy generates method definitions for decorated classes:

.. code-block:: python

    import attrs

    @attrs.define
    class A:
        one: int
        two: int = 7
        three: int = attrs.field(8)

With ``auto_attribs=False`` use ``attrs.field``:

.. code-block:: python

    @attrs.define
    class A:
        one: int = attrs.field()          # Variable annotation
        two = attrs.field()  # type: int  # Type comment
        three = attrs.field(type=int)     # type= argument

Typeshed white lie: :py:func:`attrs.field` and :py:class:`attrs.Factory` annotated to return expected types:

.. code-block:: python

    @attrs.define
    class A:
        one: int = attrs.field(8)
        two: dict[str, str] = attrs.Factory(dict)
        bad: str = attrs.field(16)   # Error: can't assign int to str

Caveats:

- Detection by function name only (custom helpers not recognized)
- Boolean arguments must be literal ``True``/``False``
- ``converter`` only supports named functions
- Validator/default decorators not type-checked
- Method definitions overwrite existing methods

.. _remote-cache:

Remote cache for faster builds
*******************************

Mypy supports remote caching to speed up builds in large codebases (10x+ speedup possible).

Components needed:

1. Shared repository for cache files keyed by commit ID
2. CI build uploading mypy cache to repository
3. Wrapper script downloading cache before running mypy

Shared repository
=================

Store ``.mypy_cache`` as downloadable artifact indexed by commit ID (build artifact, S3, web server).

CI build
========

1. Run mypy (generates ``.mypy_cache``)
2. Create tarball from ``.mypy_cache``
3. Get commit ID (``git rev-parse HEAD``)
4. Upload tarball with commit-based name

Wrapper script
==============

1. Find merge base: ``git merge-base HEAD origin/master``
2. Download cache for that commit
3. Extract to ``.mypy_cache``
4. Run mypy

Caching with mypy daemon
========================

Use :option:`--cache-fine-grained <mypy --cache-fine-grained>` in CI::

    $ mypy --cache-fine-grained <args...>

Use ``--use-fine-grained-cache`` with daemon::

    $ dmypy start -- --use-fine-grained-cache <options...>

Refinements
===========

Optional improvements:

- Skip download if merge base unchanged
- Restart daemon when branch changes (faster than incremental)
- Try last 5 commits if exact match unavailable
- Fall back to incremental if remote unavailable
- Multiple cache directories per branch with :option:`--cache-dir <mypy --cache-dir>`
- Use remote cache in CI itself

.. _extended_callable:

Extended Callable types
***********************

**Deprecated**: Use :ref:`callback protocols <callback_protocols>` instead.

Experimental extension supporting keyword arguments, optional arguments:

.. code-block:: python

   from collections.abc import Callable
   from mypy_extensions import (Arg, DefaultArg, NamedArg,
                                DefaultNamedArg, VarArg, KwArg)

   def func(__a: int,
            b: int,
            c: int = 0,
            *args: int,
            d: int,
            e: int = 0,
            **kwargs: int) -> int:
       ...

   F = Callable[[int,
                 Arg(int, 'b'),
                 DefaultArg(int, 'c'),
                 VarArg(int),
                 NamedArg(int, 'd'),
                 DefaultNamedArg(int, 'e'),
                 KwArg(int)],
                int]

   f: F = func

Available specifiers:

.. code-block:: python

   def Arg(type=Any, name=None):
       # Mandatory positional argument

   def DefaultArg(type=Any, name=None):
       # Optional positional argument

   def NamedArg(type=Any, name=None):
       # Mandatory keyword-only argument

   def DefaultNamedArg(type=Any, name=None):
       # Optional keyword-only argument

   def VarArg(type=Any):
       # *args-style variadic positional

   def KwArg(type=Any):
       # **kwargs-style variadic keyword

Basic ``Callable[[int, str, int], float]`` equivalent to ``Callable[[Arg(int), Arg(str), Arg(int)], float]``.

``Callable[..., int]`` roughly equivalent to ``Callable[[VarArg(), KwArg()], int]``.

Note: Functions return ``type`` at runtime (info not available at runtime).
