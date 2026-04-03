.. _protocol-types:

Protocols and structural subtyping
==================================

**Nominal subtyping**: Based on class hierarchy. ``Dog`` inherits ``Animal`` → ``Dog`` is subtype of ``Animal``.

**Structural subtyping**: Based on available operations. ``Dog`` is structural subtype of ``Animal`` if it has all attributes/methods of ``Animal`` with compatible types. Static equivalent of duck typing.

Predefined protocols
********************

Stdlib modules define protocol classes for common Python protocols (e.g., :py:class:`~collections.abc.Iterable`). Mypy recognizes compatible implementations:

.. code-block:: python

   from collections.abc import Iterator, Iterable

   class IntList:
       def __init__(self, value: int, next: IntList | None) -> None:
           self.value = value
           self.next = next

       def __iter__(self) -> Iterator[int]:
           current = self
           while current:
               yield current.value
               current = current.next

   def print_numbered(items: Iterable[int]) -> None:
       for n, x in enumerate(items):
           print(n + 1, x)

   print_numbered(IntList(3, IntList(5, None)))  # OK
   print_numbered([4, 5])  # OK

Note: Python 3.8 requires ``typing`` aliases (:py:class:`~typing.Iterable`). Python 3.9+ can use :py:mod:`collections.abc` directly.

Simple user-defined protocols
*****************************

Define custom protocols by inheriting ``Protocol``:

.. code-block:: python

   from collections.abc import Iterable
   from typing import Protocol

   class SupportsClose(Protocol):
       def close(self) -> None: ...

   class Resource:  # No SupportsClose base class needed
       def close(self) -> None:
          self.resource.release()

   def close_all(items: Iterable[SupportsClose]) -> None:
       for item in items:
           item.close()

   close_all([Resource(), open('some/file')])  # OK

Defining subprotocols and subclassing protocols
***********************************************

Extend protocols via multiple inheritance:

.. code-block:: python

   class SupportsRead(Protocol):
       def read(self, amount: int) -> bytes: ...

   class TaggedReadableResource(SupportsClose, SupportsRead, Protocol):
       label: str

   class AdvancedResource(Resource):
       def __init__(self, label: str) -> None:
           self.label = label

       def read(self, amount: int) -> bytes:
           ...

   resource: TaggedReadableResource
   resource = AdvancedResource('handle with care')  # OK

Inheriting from protocol without ``Protocol`` base creates regular class (uses nominal subtyping):

.. code-block:: python

   class NotAProtocol(SupportsClose):  # NOT a protocol
       new_attr: int

   class Concrete:
      new_attr: int = 0
      def close(self) -> None:
          ...

   x: NotAProtocol = Concrete()  # Error: nominal subtyping

Explicit protocol subclassing documents intent and forces mypy to verify compatibility. Omitting attribute value or method body makes it implicitly abstract:

.. code-block:: python

   class SomeProto(Protocol):
       attr: int  # No value
       def method(self) -> str: ...  # No body

   class ExplicitSubclass(SomeProto):
       pass

   ExplicitSubclass()  # Error: Cannot instantiate abstract class with abstract attributes 'attr' and 'method'

Verify implementation with assignment:

.. code-block:: python

   _proto: SomeProto = cast(ExplicitSubclass, None)

Invariance of protocol attributes
*********************************

Protocol attributes are invariant:

.. code-block:: python

   class Box(Protocol):
         content: object

   class IntBox:
         content: int

   def takes_box(box: Box) -> None: ...

   takes_box(IntBox())  # Error: expected "object", got "int"

Reason: mutable attributes allow incompatible assignments:

.. code-block:: python

   def takes_box_evil(box: Box) -> None:
       box.content = "asdf"  # Would break type safety

   my_int_box = IntBox()
   takes_box_evil(my_int_box)
   my_int_box.content + 1  # TypeError!

Fix: declare read-only with ``@property``:

.. code-block:: python

   class Box(Protocol):
       @property
       def content(self) -> object: ...

   class IntBox:
       content: int

   takes_box(IntBox(42))  # OK

Recursive protocols
*******************

Protocols can be recursive/mutually recursive:

.. code-block:: python

   from typing import Protocol

   class TreeLike(Protocol):
       value: int

       @property
       def left(self) -> TreeLike | None: ...

       @property
       def right(self) -> TreeLike | None: ...

   class SimpleTree:
       def __init__(self, value: int) -> None:
           self.value = value
           self.left: SimpleTree | None = None
           self.right: SimpleTree | None = None

   root: TreeLike = SimpleTree(0)  # OK

Using isinstance() with protocols
*********************************

Use ``@runtime_checkable`` for runtime structural checks:

.. code-block:: python

   from typing import Protocol, runtime_checkable

   @runtime_checkable
   class Portable(Protocol):
       handles: int

   class Mug:
       def __init__(self) -> None:
           self.handles = 1

   mug = Mug()
   if isinstance(mug, Portable):  # Works at runtime
      use(mug.handles)

Warning: ``isinstance`` with protocols is not fully safe. Only checks member existence, not types. ``issubclass`` only checks method existence.

Note: ``isinstance`` with protocols can be slow. Often better to use ``hasattr``.

.. _callback_protocols:

Callback protocols
******************

Define flexible callbacks using ``__call__``:

.. code-block:: python

   from collections.abc import Iterable
   from typing import Protocol

   class Combiner(Protocol):
       def __call__(self, *vals: bytes, maxlen: int | None = None) -> list[bytes]: ...

   def batch_proc(data: Iterable[bytes], cb_results: Combiner) -> bytes:
       for item in data:
           ...

   def good_cb(*vals: bytes, maxlen: int | None = None) -> list[bytes]:
       ...
   def bad_cb(*vals: bytes, maxitems: int | None) -> list[bytes]:
       ...

   batch_proc([], good_cb)  # OK
   batch_proc([], bad_cb)   # Error: different parameter name/kind

Callback protocols and :py:class:`~collections.abc.Callable` mostly interchangeable. Parameter names must match unless positional-only:

.. code-block:: python

   from collections.abc import Callable
   from typing import Protocol, TypeVar

   T = TypeVar('T')

   class Copy(Protocol):
       def __call__(self, origin: T, /) -> T: ...  # '/' marks positional-only

   copy_a: Callable[[T], T]
   copy_b: Copy

   copy_a = copy_b  # OK
   copy_b = copy_a  # OK

Binding of types in protocol attributes
***************************************

Protocol attributes treated as external types (callables not bound, descriptors not invoked):

.. code-block:: python

   from typing import Callable, Protocol

   class Example(Protocol):
       foo: Callable[[object], int]
       bar: Integer

   ex: Example
   reveal_type(ex.foo)  # Revealed type is Callable[[object], int]
   reveal_type(ex.bar)  # Revealed type is Integer

For class-level handling, use ``ClassVar``:

.. code-block:: python

   from typing import ClassVar

   class OtherExample(Protocol):
       foo: ClassVar[Callable[[object], int]]
       bar: ClassVar[Integer]

   ex2: OtherExample
   reveal_type(ex2.foo)  # Revealed type is Callable[[], int]
   reveal_type(ex2.bar)  # Revealed type is int

Predefined protocol reference
*****************************

Iteration protocols
-------------------

collections.abc.Iterable[T]

.. code-block:: python

   def __iter__(self) -> Iterator[T]

collections.abc.Iterator[T]

.. code-block:: python

   def __next__(self) -> T
   def __iter__(self) -> Iterator[T]

Collection protocols
--------------------

collections.abc.Sized

.. code-block:: python

   def __len__(self) -> int

collections.abc.Container[T]

.. code-block:: python

   def __contains__(self, x: object) -> bool

collections.abc.Collection[T]

.. code-block:: python

   def __len__(self) -> int
   def __iter__(self) -> Iterator[T]
   def __contains__(self, x: object) -> bool

One-off protocols
-----------------

collections.abc.Reversible[T]

.. code-block:: python

   def __reversed__(self) -> Iterator[T]

typing.SupportsAbs[T]

.. code-block:: python

   def __abs__(self) -> T

typing.SupportsBytes

.. code-block:: python

   def __bytes__(self) -> bytes

typing.SupportsComplex

.. code-block:: python

   def __complex__(self) -> complex

typing.SupportsFloat

.. code-block:: python

   def __float__(self) -> float

typing.SupportsInt

.. code-block:: python

   def __int__(self) -> int

typing.SupportsRound[T]

.. code-block:: python

   def __round__(self) -> T

Async protocols
---------------

collections.abc.Awaitable[T]

.. code-block:: python

   def __await__(self) -> Generator[Any, None, T]

collections.abc.AsyncIterable[T]

.. code-block:: python

   def __aiter__(self) -> AsyncIterator[T]

collections.abc.AsyncIterator[T]

.. code-block:: python

   def __anext__(self) -> Awaitable[T]
   def __aiter__(self) -> AsyncIterator[T]

Context manager protocols
--------------------------

contextlib.AbstractContextManager[T]

.. code-block:: python

   def __enter__(self) -> T
   def __exit__(self,
                exc_type: type[BaseException] | None,
                exc_value: BaseException | None,
                traceback: TracebackType | None) -> bool | None

contextlib.AbstractAsyncContextManager[T]

.. code-block:: python

   def __aenter__(self) -> Awaitable[T]
   def __aexit__(self,
                 exc_type: type[BaseException] | None,
                 exc_value: BaseException | None,
                 traceback: TracebackType | None) -> Awaitable[bool | None]
