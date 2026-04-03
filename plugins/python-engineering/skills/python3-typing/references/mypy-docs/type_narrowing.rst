.. _type-narrowing:

Type narrowing
==============

Type narrowing: convincing type checker that broader type is actually more specific (e.g., ``Shape`` → ``Square``).

Techniques:

- :ref:`type-narrowing-expressions`
- :ref:`casts`
- :ref:`type-guards`
- :ref:`typeis`

.. _type-narrowing-expressions:

Type narrowing expressions
--------------------------

Supported expressions:

- :py:func:`isinstance` - ``isinstance(obj, float)`` narrows ``obj`` to ``float``
- :py:func:`issubclass` - ``issubclass(cls, MyClass)`` narrows ``cls`` to ``Type[MyClass]``
- :py:class:`type` - ``type(obj) is int`` narrows ``obj`` to ``int``
- :py:func:`callable` - ``callable(obj)`` narrows to callable type
- ``is not None`` - narrows to non-optional form

Narrowing is contextual (limited to scope):

.. code-block:: python

  def function(arg: object):
      if isinstance(arg, int):
          reveal_type(arg)  # Revealed type: "builtins.int"
      elif isinstance(arg, str) or isinstance(arg, bool):
          reveal_type(arg)  # Revealed type: "builtins.str | builtins.bool"

          if isinstance(arg, bool):
              reveal_type(arg)  # Revealed type: "builtins.bool"

      reveal_type(arg)  # Revealed type: "builtins.object"

Mypy understands ``return`` and exception implications:

.. code-block:: python

  def function(arg: int | str):
      if isinstance(arg, int):
          return

      reveal_type(arg)  # Revealed type: "builtins.str"

``assert`` narrows types:

.. code-block:: python

  def function(arg: Any):
      assert isinstance(arg, int)
      reveal_type(arg)  # Revealed type: "builtins.int"

With :option:`--warn-unreachable <mypy --warn-unreachable>`, impossible narrowing is error:

.. code-block:: python

   def function(arg: int):
       assert isinstance(arg, str)  # Error: Subclass of "int" and "str" cannot exist
       print("unreachable")  # Error: Statement is unreachable

Without ``--warn-unreachable``, mypy doesn't check unreachable code.

issubclass
~~~~~~~~~~

.. code-block:: python

   class MyCalcMeta(type):
       @classmethod
       def calc(cls) -> int:
           ...

   def f(o: object) -> None:
       t = type(o)  # Must use variable
       reveal_type(t)  # Revealed type is "builtins.type"

       if issubclass(t, MyCalcMeta):
           reveal_type(t)  # Revealed type is "Type[MyCalcMeta]"
           t.calc()  # OK

callable
~~~~~~~~

Split unions into callable/non-callable:

.. code-block:: python

  from collections.abc import Callable

  x: int | Callable[[], int]

  if callable(x):
      reveal_type(x)  # Revealed type is "def () -> builtins.int"
  else:
      reveal_type(x)  # Revealed type is "builtins.int"

.. _casts:

Casts
-----

:py:func:`~typing.cast` provides type hints to checker (no runtime check):

.. code-block:: python

   from typing import cast

   o: object = [1]
   x = cast(list[int], o)  # OK
   y = cast(list[str], o)  # OK (no runtime check)

Use assertions for runtime checks:

.. code-block:: python

   def foo(o: object) -> None:
       print(o + 5)  # Error: can't add 'object' and 'int'
       assert isinstance(o, int)
       print(o + 5)  # OK: type is 'int' here

No cast needed for ``Any`` (already permissive). Can cast to ``Any`` to allow any operations:

.. code-block:: python

    from typing import cast, Any

    x = 1
    x.whatever()  # Error
    y = cast(Any, x)
    y.whatever()  # OK (runtime error)

.. _type-guards:

User-Defined Type Guards
------------------------

PEP 647 ``TypeGuard`` - "smart" bool for conditional narrowing.

Regular bool doesn't narrow:

.. code-block:: python

  def is_str_list(val: list[object]) -> bool:
    return all(isinstance(x, str) for x in val)

  def func1(val: list[object]) -> None:
      if is_str_list(val):
          reveal_type(val)  # list[object]
          print(" ".join(val)) # Error

With ``TypeGuard``:

.. code-block:: python

  from typing import TypeGuard

  def is_str_list(val: list[object]) -> TypeGuard[list[str]]:
      return all(isinstance(x, str) for x in val)

  def func1(val: list[object]) -> None:
      if is_str_list(val):
          reveal_type(val)  # list[str]
          print(" ".join(val)) # OK

Note: Narrowing not strict (can narrow ``str`` to ``int``). Assumes developer interested in type safety.

Generic TypeGuards
~~~~~~~~~~~~~~~~~~

.. code-block:: python

  from typing import TypeGuard

  def is_two_element_tuple[T](val: tuple[T, ...]) -> TypeGuard[tuple[T, T]]:
      return len(val) == 2

  def func(names: tuple[str, ...]):
      if is_two_element_tuple(names):
          reveal_type(names)  # tuple[str, str]
      else:
          reveal_type(names)  # tuple[str, ...]

TypeGuards with parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

  def is_set_of[T](val: set[Any], type: type[T]) -> TypeGuard[set[T]]:
      return all(isinstance(x, type) for x in val)

  items: set[Any]
  if is_set_of(items, str):
      reveal_type(items)  # set[str]

TypeGuards as methods
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

  class StrValidator:
      def is_valid(self, instance: object) -> TypeGuard[str]:
          return isinstance(instance, str)

  def func(to_validate: object) -> None:
      if StrValidator().is_valid(to_validate):
          reveal_type(to_validate)  # "builtins.str"

Note: ``TypeGuard`` doesn't narrow ``self`` or ``cls``. Pass as explicit argument if needed:

.. code-block:: python

    class Parent:
        def method(self) -> None:
            reveal_type(self)  # Parent
            if is_child(self):
                reveal_type(self)  # Child

    class Child(Parent):
        ...

    def is_child(instance: Parent) -> TypeGuard[Child]:
        return isinstance(instance, Child)

Assignment expressions as TypeGuards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

  def is_float(a: object) -> TypeGuard[float]:
      return isinstance(a, float)

  def main(a: object) -> None:
      if is_float(x := a):
          reveal_type(x)  # float
          reveal_type(a)  # object
      reveal_type(x)  # object

.. _typeis:

TypeIs
------

PEP 742 - narrows type in both ``if`` and ``else`` branches:

.. code-block:: python

    from typing import TypeIs

    def is_str(x: object) -> TypeIs[str]:
        return isinstance(x, str)

    def process(x: int | str) -> None:
        if is_str(x):
            reveal_type(x)  # str
            print(x.upper())
        else:
            reveal_type(x)  # int
            print(x + 1)

Key points:

- Must accept at least one positional argument
- Return type ``TypeIs[T]``
- Must return ``bool``
- ``if`` branch: type narrowed to intersection of original and ``T``
- ``else`` branch: type narrowed to intersection of original and complement of ``T``

TypeIs vs TypeGuard
~~~~~~~~~~~~~~~~~~~

Differences:

- **TypeIs** narrows in both branches; **TypeGuard** only in ``if`` branch
- **TypeIs** requires ``T`` compatible with input type; **TypeGuard** doesn't
- **TypeIs** may infer more precise type by combining existing info with ``T``

TypeGuard example:

.. code-block:: python

    from typing import TypeGuard

    def is_str(x: object) -> TypeGuard[str]:
        return isinstance(x, str)

    def process(x: int | str) -> None:
        if is_str(x):
            reveal_type(x)  # str
            print(x.upper())
        else:
            reveal_type(x)  # int | str (not narrowed)
            print(x + 1)  # Error

Generic TypeIs
~~~~~~~~~~~~~~

.. code-block:: python

    from typing import TypeVar, TypeIs

    T = TypeVar('T')

    def is_two_element_tuple(val: tuple[T, ...]) -> TypeIs[tuple[T, T]]:
        return len(val) == 2

    def process(names: tuple[str, ...]) -> None:
        if is_two_element_tuple(names):
            reveal_type(names)  # tuple[str, str]
        else:
            reveal_type(names)  # tuple[str, ...]

TypeIs with Additional Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Type narrowing applies only to first argument:

.. code-block:: python

    from typing import Any, TypeVar, TypeIs

    T = TypeVar('T')

    def is_instance_of(val: Any, typ: type[T]) -> TypeIs[T]:
        return isinstance(val, typ)

    def process(x: Any) -> None:
        if is_instance_of(x, int):
            reveal_type(x)  # int
        else:
            reveal_type(x)  # Any

TypeIs in Methods
~~~~~~~~~~~~~~~~~

In instance/class methods, narrowing applies to second parameter (after ``self``/``cls``):

.. code-block:: python

    class Validator:
        def is_valid(self, instance: object) -> TypeIs[str]:
            return isinstance(instance, str)

        def process(self, to_validate: object) -> None:
            if Validator().is_valid(to_validate):
                reveal_type(to_validate)  # str

Assignment Expressions with TypeIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def is_float(x: object) -> TypeIs[float]:
        return isinstance(x, float)

    def main(a: object) -> None:
        if is_float(x := a):
            reveal_type(x)  # float
            print(x + 1.0)

Limitations
-----------

Mypy doesn't track cross-variable relationships:

.. code-block:: python

    class C:
        pass

    def f(a: C | None, b: C | None) -> C:
        if a is not None or b is not None:
            return a or b  # Error: got "C | None", expected "C"
        return C()

Workarounds:

- Use ``assert``
- Use cast
- Rewrite more explicitly:

.. code-block:: python

    def f(a: C | None, b: C | None) -> C:
        if a is not None:
            return a
        elif b is not None:
            return b
        return C()
