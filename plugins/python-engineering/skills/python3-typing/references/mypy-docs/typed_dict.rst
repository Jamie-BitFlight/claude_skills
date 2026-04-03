.. _typeddict:

TypedDict
*********

``TypedDict`` provides precise types for dicts with fixed string keys:

.. code-block:: python

   from typing import TypedDict

   Movie = TypedDict('Movie', {'name': str, 'year': int})

   movie: Movie = {'name': 'Blade Runner', 'year': 1982}

Type annotation on ``movie`` is important (without it, mypy infers regular ``dict`` type).

Note: If TypedDict used in function argument, passed value inferred as TypedDict without annotation.

Usage:

.. code-block:: python

   name = movie['name']  # OK; type is str
   year = movie['year']  # OK; type is int

   director = movie['director']  # Error: 'director' is not valid key

Runtime-computed keys rejected. Only string literals allowed as keys.

TypedDict acts as constructor (returns regular :py:class:`dict` at runtime):

.. code-block:: python

   toy_story = Movie(name='Toy Story', year=1995)

Equivalent to ``{'name': 'Toy Story', 'year': 1995}`` but explicit about type.

TypedDicts can nest and be used in containers. Uses structural compatibility (extra items allowed):

.. code-block:: python

   # TypedDict with extra items is subtype of narrower TypedDict (if item types compatible)

TypedDict not subtype of ``dict[...]`` (dict allows arbitrary keys). Compatible with ``Mapping[str, object]`` (read-only):

.. code-block:: python

   def print_typed_dict(obj: Mapping[str, object]) -> None:
       for key, value in obj.items():
           print(f'{key}: {value}')

   print_typed_dict(Movie(name='Toy Story', year=1995))  # OK

Note: Python <3.8 requires ``typing_extensions``: ``python3 -m pip install --upgrade typing-extensions``

Totality
--------

By default all keys required:

.. code-block:: python

   toy_story: Movie = {'name': 'Toy Story'}  # Error: 'year' missing

Use ``total=False`` for optional keys:

.. code-block:: python

   GuiOptions = TypedDict(
       'GuiOptions', {'language': str, 'color': str}, total=False)
   options: GuiOptions = {}  # OK
   options['language'] = 'en'

Use :py:meth:`~dict.get` for partial TypedDicts (mypy still allows ``[]`` but could fail at runtime).

Non-required keys shown with ``?`` in error messages:

.. code-block:: python

   # Revealed type is "TypedDict('GuiOptions', {'language'?: builtins.str,
   #                                            'color'?: builtins.str})"
   reveal_type(options)

Totality affects structural compatibility. Partial and total TypedDicts incompatible.

Supported operations
--------------------

Supported subset of dict operations (must use string literals as keys):

* :py:class:`~collections.abc.Mapping` operations:

  * ``d[key]``
  * ``key in d``
  * ``len(d)``
  * ``for key in d``
  * :py:meth:`d.get(key[, default]) <dict.get>`
  * :py:meth:`d.keys() <dict.keys>`
  * :py:meth:`d.values() <dict.values>`
  * :py:meth:`d.items() <dict.items>`

* :py:meth:`d.copy() <dict.copy>`
* :py:meth:`d.setdefault(key, default) <dict.setdefault>`
* :py:meth:`d1.update(d2) <dict.update>`
* :py:meth:`d.pop(key[, default]) <dict.pop>` (partial only)
* ``del d[key]`` (partial only)

Note: :py:meth:`~dict.clear` and :py:meth:`~dict.popitem` not supported (could delete required items invisible to mypy due to structural subtyping).

Class-based syntax
------------------

Alternative syntax (Python 3.6+):

.. code-block:: python

   class Movie(TypedDict):
       name: str
       year: int

Equivalent to functional definition. Doesn't define real class. Supports inheritance (notational shortcut, structural compatibility still applies):

.. code-block:: python

   class Movie(TypedDict):
       name: str
       year: int

   class BookBasedMovie(Movie):
       based_on: str

``BookBasedMovie`` has keys ``name``, ``year``, ``based_on``.

Mixing required and non-required items
--------------------------------------

Use inheritance with ``total=False``:

.. code-block:: python

   class MovieBase(TypedDict):
       name: str
       year: int

   class Movie(MovieBase, total=False):
       based_on: str

``Movie`` has required ``name``, ``year``; optional ``based_on``.

Compatibility: requires all required keys in other TypedDict are required, all non-required are non-required.

Read-only items
---------------

Use ``typing.ReadOnly`` (Python 3.13) or ``typing_extensions.ReadOnly`` (PEP 705):

.. code-block:: python

    from typing import TypedDict
    from typing_extensions import ReadOnly

    class Movie(TypedDict):
        name: ReadOnly[str]
        num_watched: int

    m: Movie = {"name": "Jaws", "num_watched": 1}
    m["name"] = "The Godfather"  # Error: "name" is read-only
    m["num_watched"] += 1  # OK

Mutable item TypedDict can be assigned to read-only item TypedDict. Item types can vary covariantly:

.. code-block:: python

    class Entry(TypedDict):
        name: ReadOnly[str | None]
        year: ReadOnly[int]

    class Movie(TypedDict):
        name: str
        year: int

    def process_entry(i: Entry) -> None: ...

    m: Movie = {"name": "Jaws", "year": 1975}
    process_entry(m)  # OK

Unions of TypedDicts
--------------------

Cannot use ``isinstance`` to distinguish TypedDict variants (all are regular dicts at runtime).

Use :ref:`tagged union pattern <tagged_unions>`: give each TypedDict same key with unique :ref:`Literal type <literal_types>`, then check that key.

Inline TypedDict types
----------------------

Experimental (use ``--enable-incomplete-feature=InlineTypedDict``):

.. code-block:: python

    def test_values() -> {"width": int, "description": str}:
        return {"width": 42, "description": "test"}

    class Response(TypedDict):
        status: int
        msg: str
        content: {"items": list[{"key": str, "value": str}]}

Type alias usage requires explicit type alias forms:

.. code-block:: python

    from typing import TypeAlias

    X = {"a": int, "b": int}  # creates dict[str, type[int]] variable
    Y: TypeAlias = {"a": int, "b": int}  # creates type alias
    type Z = {"a": int, "b": int}  # same (Python 3.12+)

Avoid inline syntax in union types (incompatible with runtime type-checking).
