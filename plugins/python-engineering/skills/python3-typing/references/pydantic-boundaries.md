# Pydantic Boundary Patterns

## Strict Mode

Always use strict mode for boundary models to catch producer bugs:

```python
from pydantic import BaseModel

class IncomingPayload(BaseModel):
    user_id: int
    email: str
    model_config = {"strict": True}
```

## TypeAdapter for Ad-hoc Validation

```python
from pydantic import TypeAdapter

user_list_adapter = TypeAdapter(list[IncomingPayload])
users = user_list_adapter.validate_python(raw_data)
```

## Validators

```python
from pydantic import BaseModel, field_validator

class Config(BaseModel):
    host: str
    port: int

    @field_validator("port")
    @classmethod
    def port_in_range(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("port must be 1-65535")
        return v
```

## Nested Models

```python
class Address(BaseModel):
    street: str
    city: str

class User(BaseModel):
    name: str
    address: Address  # nested validation
```

## Discriminated Unions

```python
from pydantic import BaseModel, Field
from typing import Literal

class Cat(BaseModel):
    pet_type: Literal["cat"]
    meows: int

class Dog(BaseModel):
    pet_type: Literal["dog"]
    barks: float

Pet = Cat | Dog
```
