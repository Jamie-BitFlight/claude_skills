# CASE: additional LSP-2 and ISP-1 violations plus one DECOY.
# DECOY: AbstractReader is a broad interface that LOOKS like an ISP-1 violation
# (fat interface), but every implementer genuinely uses all methods because the
# interface models a file-like object contract where open/read/close are inseparable.
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


# VIOLATION ISP-1: IDeviceController forces all implementers to define methods they
# cannot meaningfully support.  A temperature sensor cannot reboot; a relay cannot read.
class IDeviceController(ABC):
    @abstractmethod
    def read_value(self) -> float: ...

    @abstractmethod
    def write_value(self, value: float) -> None: ...

    @abstractmethod
    def reboot(self) -> None: ...

    @abstractmethod
    def get_firmware_version(self) -> str: ...


class TemperatureSensor(IDeviceController):
    def read_value(self) -> float:
        return 22.5

    def write_value(self, value: float) -> None:
        # Sensor cannot be written to — forced by the fat interface
        raise NotImplementedError("TemperatureSensor is read-only")

    def reboot(self) -> None:
        # Sensor has no reboot capability — forced by the fat interface
        raise NotImplementedError("TemperatureSensor cannot reboot")

    def get_firmware_version(self) -> str:
        return "sensor-1.0"


class Relay(IDeviceController):
    def __init__(self) -> None:
        self._state: float = 0.0

    def read_value(self) -> float:
        # Relay state can be read, but the method is misnamed for this device
        return self._state

    def write_value(self, value: float) -> None:
        self._state = value

    def reboot(self) -> None:
        self._state = 0.0

    def get_firmware_version(self) -> str:
        raise NotImplementedError("Relay has no firmware version")


# VIOLATION LSP-2: XmlSerializer.serialize raises TypeError on inputs the base
# accepts, changing the exception contract.
class BaseSerializer(ABC):
    @abstractmethod
    def serialize(self, data: dict) -> str: ...

    @abstractmethod
    def deserialize(self, text: str) -> dict: ...


class JsonSerializer(BaseSerializer):
    def serialize(self, data: dict) -> str:
        import json  # noqa: PLC0415

        return json.dumps(data)

    def deserialize(self, text: str) -> dict:
        import json  # noqa: PLC0415

        return json.loads(text)


class XmlSerializer(BaseSerializer):
    def serialize(self, data: dict) -> str:
        # Raises TypeError instead of a serialization error — changes the exception contract.
        # Callers holding a BaseSerializer reference cannot anticipate TypeError here.
        if not all(isinstance(k, str) for k in data):
            raise TypeError("XmlSerializer requires string keys")
        parts = [f"<{k}>{v}</{k}>" for k, v in data.items()]
        return f"<root>{''.join(parts)}</root>"

    def deserialize(self, text: str) -> dict:
        # Stub — not the focus of this case
        return {}


# DECOY: AbstractReader has three methods (open/read/close) that LOOK like a fat
# interface (ISP-1), but every concrete implementer must implement all three because
# the contract models a resource lifecycle where skipping any method is meaningless.
# A cheap reviewer may flag this as ISP-1 because it is abstract and has three methods,
# but the interface is correctly minimal — no implementer is forced to define a method
# it does not use.
class AbstractReader(ABC):
    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def read(self) -> str: ...

    @abstractmethod
    def close(self) -> None: ...


class FileReader(AbstractReader):
    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle = None

    def open(self) -> None:
        self._handle = self._path.open(encoding="utf-8")

    def read(self) -> str:
        if self._handle is None:
            raise RuntimeError("FileReader not opened")
        return self._handle.read()

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
