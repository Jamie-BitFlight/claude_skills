Generics
========

Defining generic classes
************************

Python 3.12+ syntax (preferred):

.. code-block:: python

   class Stack[T]:
       def __init__(self) -> None:
           self.items: list[T] = []
       def push(self, item: T) -> None:
           self.items.append(item)
       def pop(self) -> T:
           return self.items.pop()

Legacy syntax (Python 3.11 and earlier, still supported):

.. code-block:: python

   from typing import TypeVar, Generic

   T = TypeVar('T')

   class Stack(Generic[T]):
       def __init__(self) -> None:
           self.items: list[T] = []
       def push(self, item: T) -> None:
           self.items.append(item)
       def pop(self) -> T:
           return self.items.pop()

Usage:

.. code-block:: python

   stack = Stack[int]()
   stack.push(2)
   stack.push('x')  # Error: incompatible type "str"; expected "int"

Constructor form with type inference:

.. code-block:: python

   class Box[T]:
       def __init__(self, content: T) -> None:
           self.content = content

   Box(1)       # OK, inferred type is Box[int]
   Box[int](1)  # Also OK
   Box[int]('some string')  # Error: incompatible type "str"; expected "int"

Terminology: ``T`` in ``class Stack[T]`` is a *type parameter* or *type variable*. ``Stack[int]`` uses ``int`` as a *type argument*.

Defining subclasses of generic classes
**************************************

.. code-block:: python

   from typing import Mapping, Iterator

   # Generic subclass (Python 3.12+)
   class MyMap[KT, VT](Mapping[KT, VT]):
       def __getitem__(self, k: KT) -> VT: ...
       def __iter__(self) -> Iterator[KT]: ...
       def __len__(self) -> int: ...

   items: MyMap[str, int]  # OK

   # Non-generic subclass
   class StrDict(dict[str, str]):
       def __str__(self) -> str:
           return f'StrDict({super().__str__()})'

   data: StrDict[int, int]  # Error: StrDict is not generic
   data2: StrDict  # OK

Legacy syntax:

.. code-block:: python

   from typing import Generic, TypeVar, Mapping, Iterator

   KT = TypeVar('KT')
   VT = TypeVar('VT')

   class MyMap(Mapping[KT, VT]):
       def __getitem__(self, k: KT) -> VT: ...
       def __iter__(self) -> Iterator[KT]: ...
       def __len__(self) -> int: ...

Note: Explicit :py:class:`~collections.abc.Mapping` base required for mypy to recognize mapping (doesn't use structural subtyping for ABCs like Mapping/Sequence).

Legacy syntax type parameter ordering rules:

* If ``Generic[...]`` present, parameter order determined by its order
* Without ``Generic[...]``, parameters collected lexicographically (first appearance)

.. code-block:: python

   from typing import Generic, TypeVar, Any

   T = TypeVar('T')
   S = TypeVar('S')
   U = TypeVar('U')

   class First(One[T], Another[S]): ...
   x: First[int, str]        # T=int, S=str

   class Second(One[T], Another[S], Generic[S, U, T]): ...
   y: Second[int, str, Any]  # T=Any, S=int, U=str

Python 3.12 syntax requires explicit type parameters in ``[...]`` after class name; ``Generic[...]`` base never used.

Generic functions
*****************

Python 3.12+ syntax:

.. code-block:: python

   from collections.abc import Sequence

   def first[T](seq: Sequence[T]) -> T:
       return seq[0]

Legacy syntax:

.. code-block:: python

   from typing import TypeVar, Sequence

   T = TypeVar('T')

   def first(seq: Sequence[T]) -> T:
       return seq[0]

Type inference:

.. code-block:: python

   reveal_type(first([1, 2, 3]))   # Revealed type is "builtins.int"
   reveal_type(first(('a', 'b')))  # Revealed type is "builtins.str"

Legacy syntax allows sharing TypeVar definitions across functions:

.. code-block:: python

   T = TypeVar('T')

   def first(seq: Sequence[T]) -> T:
       return seq[0]

   def last(seq: Sequence[T]) -> T:
       return seq[-1]

Type variables must be bound in containing generic class/function. Cannot explicitly pass type arguments:

.. code-block:: python

   first[int]([1, 2])  # Error: can't use [...] with generic function

Workaround: Define generic class with ``__call__`` method.

Type variables with upper bounds
********************************

Restrict type variable to subtypes of specific type using ``T: <bound>`` (Python 3.12+):

.. code-block:: python

   from typing import SupportsAbs

   def max_by_abs[T: SupportsAbs[float]](*xs: T) -> T:
       return max(xs, key=abs)

Legacy syntax with ``bound=``:

.. code-block:: python

   from typing import TypeVar, SupportsAbs

   T = TypeVar('T', bound=SupportsAbs[float])

   def max_by_abs(*xs: T) -> T:
       return max(xs, key=abs)

Usage:

.. code-block:: python

   max_by_abs(-3.5, 2)   # OK, type 'float'
   max_by_abs(5+6j, 7)   # OK, type 'complex'
   max_by_abs('a', 'b')  # Error: 'str' not subtype of SupportsAbs[float]

Generic methods and generic self
********************************

Generic ``self`` for method chaining (Python 3.12+):

.. code-block:: python

   class Shape:
       def set_scale[T: Shape](self: T, scale: float) -> T:
           self.scale = scale
           return self

   class Circle(Shape):
       def set_radius(self, r: float) -> 'Circle':
           self.radius = r
           return self

   circle: Circle = Circle().set_scale(0.5).set_radius(2.7)  # OK

Legacy syntax:

.. code-block:: python

   from typing import TypeVar

   T = TypeVar('T', bound='Shape')

   class Shape:
       def set_scale(self: T, scale: float) -> T:
           self.scale = scale
           return self

Generic ``cls`` for class methods (Python 3.12+):

.. code-block:: python

   class Friend:
       other: "Friend | None" = None

       @classmethod
       def make_pair[T: Friend](cls: type[T]) -> tuple[T, T]:
           a, b = cls(), cls()
           a.other = b
           b.other = a
           return a, b

Legacy syntax:

.. code-block:: python

   T = TypeVar('T', bound='Friend')

   @classmethod
   def make_pair(cls: type[T]) -> tuple[T, T]:
       a, b = cls(), cls()
       a.other = b
       b.other = a
       return a, b

Overriding methods with generic ``self`` must return generic ``self`` or instance of current class.

Mypy allows unsafe uses of generic self in arguments (common pattern, rarely causes issues):

.. code-block:: python

   class Base:
       def compare[T: Base](self: T, other: T) -> bool:
           return False

   class Sub(Base):
       def __init__(self, x: int) -> None:
           self.x = x

       # Unsafe but allowed
       def compare(self, other: 'Sub') -> bool:
           return self.x > other.x

   b: Base = Sub(42)
   b.compare(Base())  # Runtime error: 'Base' has no attribute 'x'

Automatic self types using typing.Self
**************************************

Simpler syntax using ``Self`` (PEP 673):

.. code-block:: python

   from typing import Self

   class Friend:
       other: Self | None = None

       @classmethod
       def make_pair(cls) -> tuple[Self, Self]:
           a, b = cls(), cls()
           a.other = b
           b.other = a
           return a, b

Note: Python <3.11 requires ``from typing_extensions import Self`` (version 4.0+).

Variance of generic types
*************************

Three kinds of variance: invariant, covariant, contravariant.

If ``B`` is subtype of ``A``:

* ``MyCovGen[T]`` is **covariant** if ``MyCovGen[B]`` is subtype of ``MyCovGen[A]``
* ``MyContraGen[T]`` is **contravariant** if ``MyContraGen[A]`` is subtype of ``MyContraGen[B]``
* ``MyInvGen[T]`` is **invariant** if neither above holds

Examples:

.. code-block:: python

   class Shape: ...
   class Triangle(Shape): ...

   # Covariant: immutable containers (Sequence, frozenset)
   def count_lines(shapes: Sequence[Shape]) -> int:
       return sum(shape.num_sides for shape in shapes)

   triangles: Sequence[Triangle]
   count_lines(triangles)  # OK

   # Contravariant: Callable arguments
   def cost_of_paint_required(
       triangle: Triangle,
       area_calculator: Callable[[Triangle], float]
   ) -> float:
       return area_calculator(triangle) * DOLLAR_PER_SQ_FT

   def area_of_any_shape(shape: Shape) -> float: ...
   cost_of_paint_required(triangle, area_of_any_shape)  # OK

   # Invariant: mutable containers (list, dict)
   class Circle(Shape):
       def rotate(self): ...

   def add_one(things: list[Shape]) -> None:
       things.append(Shape())

   my_circles: list[Circle] = []
   add_one(my_circles)     # Error: would allow Shape in list[Circle]
   my_circles[0].rotate()  # Would fail at runtime

Python 3.12 syntax infers variance automatically. Covariance requires:
- Private attributes (underscore prefix) OR
- ``Final`` attributes

.. code-block:: python

   class Box[T]:  # Implicitly covariant
       def __init__(self, content: T) -> None:
           self._content = content  # Private attribute
       def get_content(self) -> T:
           return self._content

   # Also covariant with Final
   from typing import Final

   class Box[T]:
       def __init__(self, content: T) -> None:
           self.content: Final = content
       def get_content(self) -> T:
           return self.content

Legacy syntax: specify variance explicitly:

.. code-block:: python

   from typing import Generic, TypeVar

   T_co = TypeVar('T_co', covariant=True)

   class Box(Generic[T_co]):
       def __init__(self, content: T_co) -> None:
           self._content = content
       def get_content(self) -> T_co:
           return self._content

Type variables with value restriction
*************************************

Restrict type variable to specific set of types using ``T: (type1, type2)`` (Python 3.12+):

.. code-block:: python

   def concat[S: (str, bytes)](x: S, y: S) -> S:
       return x + y

   concat('a', 'b')    # OK
   concat(b'a', b'b')  # OK
   concat(1, 2)        # Error
   concat('string', b'bytes')  # Error: can't mix types

Legacy syntax:

.. code-block:: python

   AnyStr = TypeVar('AnyStr', str, bytes)

   def concat(x: AnyStr, y: AnyStr) -> AnyStr:
       return x + y

Different from union: enforces same type for all uses.

Subtype promotion to valid value:

.. code-block:: python

   class S(str): pass

   ss = concat(S('foo'), S('bar'))
   reveal_type(ss)  # Revealed type is "builtins.str"

Note: ``typing.AnyStr`` is deprecated but means same as ``TypeVar('AnyStr', str, bytes)``.

Cannot have both value restriction and upper bound.

Declaring decorators
********************

Basic decorator preserving signature (Python 3.12+):

.. code-block:: python

   from collections.abc import Callable
   from typing import Any, cast

   def printing_decorator[F: Callable[..., Any]](func: F) -> F:
       def wrapper(*args, **kwds):
           print("Calling", func)
           return func(*args, **kwds)
       return cast(F, wrapper)

   @printing_decorator
   def add_forty_two(value: int) -> int:
       return value + 42

   reveal_type(add_forty_two(3))  # Revealed type is "builtins.int"
   add_forty_two('x')  # Error: incompatible type "str"; expected "int"

Legacy syntax:

.. code-block:: python

   from typing import TypeVar, Callable, Any, cast

   F = TypeVar('F', bound=Callable[..., Any])

   def printing_decorator(func: F) -> F:
       def wrapper(*args, **kwds):
           print("Calling", func)
           return func(*args, **kwds)
       return cast(F, wrapper)

Using parameter specification for better type safety (Python 3.12+):

.. code-block:: python

   def printing_decorator[**P, T](func: Callable[P, T]) -> Callable[P, T]:
       def wrapper(*args: P.args, **kwds: P.kwargs) -> T:
           print("Calling", func)
           return func(*args, **kwds)
       return wrapper

Legacy syntax with ParamSpec:

.. code-block:: python

   from typing_extensions import ParamSpec

   P = ParamSpec('P')
   T = TypeVar('T')

   def printing_decorator(func: Callable[P, T]) -> Callable[P, T]:
       def wrapper(*args: P.args, **kwds: P.kwargs) -> T:
           print("Calling", func)
           return func(*args, **kwds)
       return wrapper

Altering signature (Python 3.12+):

.. code-block:: python

   # Replace return type
   def stringify[**P, T](func: Callable[P, T]) -> Callable[P, str]:
       def wrapper(*args: P.args, **kwds: P.kwargs) -> str:
           return str(func(*args, **kwds))
       return wrapper

   # Insert argument
   from typing import Concatenate

   def printing_decorator[**P, T](func: Callable[P, T]) -> Callable[Concatenate[str, P], T]:
       def wrapper(msg: str, /, *args: P.args, **kwds: P.kwargs) -> T:
           print("Calling", func, "with", msg)
           return func(*args, **kwds)
       return wrapper

Decorator factories
-------------------

Python 3.12+:

.. code-block:: python

   def route[F: Callable[..., Any]](url: str) -> Callable[[F], F]:
       ...

   @route(url='/')
   def index(request: Any) -> str:
       return 'Hello world'

Legacy syntax:

.. code-block:: python

   F = TypeVar('F', bound=Callable[..., Any])

   def route(url: str) -> Callable[[F], F]:
       ...

Bare and parameterized decorator with ``@overload`` (Python 3.12+):

.. code-block:: python

   from typing import overload

   @overload
   def atomic[F: Callable[..., Any]](func: F, /) -> F: ...
   @overload
   def atomic[F: Callable[..., Any]](*, savepoint: bool = True) -> Callable[[F], F]: ...

   def atomic(func: Callable[..., Any] | None = None, /, *, savepoint: bool = True):
       def decorator(func: Callable[..., Any]):
           ...
       if func is not None:
           return decorator(func)
       else:
           return decorator

   @atomic
   def func1() -> None: ...

   @atomic(savepoint=False)
   def func2() -> None: ...

Generic protocols
*****************

Python 3.12+:

.. code-block:: python

   from typing import Protocol

   class Box[T](Protocol):
       content: T

   def do_stuff(one: Box[str], other: Box[bytes]) -> None:
       ...

   class StringWrapper:
       def __init__(self, content: str) -> None:
           self.content = content

   do_stuff(StringWrapper('one'), BytesWrapper(b'other'))  # OK

   x: Box[float] = ...
   y: Box[int] = ...
   x = y  # Error: Box is invariant

Legacy syntax:

.. code-block:: python

   T = TypeVar('T')

   class Box(Protocol[T]):
       content: T

Note: ``Protocol[T]`` is shorthand for ``Protocol, Generic[T]`` in legacy syntax.

Legacy syntax checks declared variance matches usage:

.. code-block:: python

   T = TypeVar('T')

   class ReadOnlyBox(Protocol[T]):  # Error: Invariant type variable used where covariant expected
       def content(self) -> T: ...

   # Correct with covariant type variable
   T_co = TypeVar('T_co', covariant=True)

   class ReadOnlyBox(Protocol[T_co]):
       def content(self) -> T_co: ...

   ax: ReadOnlyBox[float] = ...
   ay: ReadOnlyBox[int] = ...
   ax = ay  # OK: ReadOnlyBox is covariant

Recursive protocols (Python 3.12+):

.. code-block:: python

   class Linked[T](Protocol):
       val: T
       def next(self) -> 'Linked[T]': ...

   class L:
       val: int
       def next(self) -> 'L': ...

   def last(seq: Linked[T]) -> T: ...

   result = last(L())
   reveal_type(result)  # Revealed type is "builtins.int"

Generic type aliases
********************

Python 3.12+ uses ``type`` statement:

.. code-block:: python

   from collections.abc import Callable, Iterable

   type TInt[S] = tuple[int, S]
   type UInt[S] = S | int
   type CBack[S] = Callable[..., S]

   def response(query: str) -> UInt[str]:  # Same as str | int
       ...

   table_entry: TInt  # Same as tuple[int, Any]

   type Vec[T: (int, float, complex)] = Iterable[tuple[T, T]]

   def inproduct[T: (int, float, complex)](v: Vec[T]) -> T:
       return sum(x*y for x, y in v)

   v1: Vec[int] = []      # Same as Iterable[tuple[int, int]]
   v2: Vec = []           # Same as Iterable[tuple[Any, Any]]
   v3: Vec[int, int] = [] # Error: too many type arguments

Legacy syntax:

.. code-block:: python

   from typing import TypeVar, Iterable, Union, Callable

   S = TypeVar('S')

   TInt = tuple[int, S]  # 1 type parameter (only S is free)
   UInt = Union[S, int]
   CBack = Callable[..., S]

   T = TypeVar('T', int, float, complex)
   Vec = Iterable[tuple[T, T]]

   v1: Vec[int] = []      # Same as Iterable[tuple[int, int]]
   v2: Vec = []           # Same as Iterable[tuple[Any, Any]]

Type aliases defined with ``type`` statement:
- Can't be used as base classes
- Can't be used to construct instances

Legacy syntax aliases can do both.

Differences between new and old syntax
**************************************

Key differences:

* New syntax type variables scoped to class/function; old syntax creates namespace-level definitions
* Old syntax allows sharing TypeVar definitions; new syntax doesn't
* New syntax infers variance automatically; old syntax requires explicit declaration
* New syntax allows forward/recursive references without string escaping
* New syntax allows generic alias without type parameter reference
* New syntax aliases can't be base classes or constructors; old syntax aliases can

Generic class internals
***********************

At runtime, indexing returns generic alias that instantiates original class:

.. code-block:: python

   >>> class Stack[T]: ...
   >>> Stack
   __main__.Stack
   >>> Stack[int]
   __main__.Stack[int]
   >>> instance = Stack[int]()
   >>> instance.__class__
   __main__.Stack

Type variables erased at runtime. ``typing.Generic`` included as implicit base:

.. code-block:: python

   >>> class Stack[T]: ...
   >>> Stack.mro()
   [<class '__main__.Stack'>, <class 'typing.Generic'>, <class 'object'>]

Python 3.8 and earlier: use :py:mod:`typing` aliases (:py:class:`~typing.List`, :py:class:`~typing.Dict`) since built-ins don't support indexing.

.. code-block:: python

   >>> from typing import List
   >>> List[int]
   typing.List[int]

Note: ``typing`` aliases don't support construction:

.. code-block:: python

   >>> list[int]()
   []
   >>> from typing import List
   >>> List[int]()
   TypeError: Type List cannot be instantiated; use list() instead
