# CASE: ISP violations — fat interface (ISP-1), broad client dependency (ISP-2).
# DECOY: ReportFacade looks like a god interface but is a legitimate Facade pattern —
# it exposes a unified API over three segregated services and does not force any
# implementer to define methods it doesn't use.
from __future__ import annotations

from abc import ABC, abstractmethod


# VIOLATION ISP-1: IWorker is a fat interface that forces all implementers to define
# methods they do not use.  A robot cannot eat; a part-timer has no benefits.
class IWorker(ABC):
    @abstractmethod
    def work(self) -> None: ...

    @abstractmethod
    def eat(self) -> None: ...

    @abstractmethod
    def sleep(self) -> None: ...

    @abstractmethod
    def claim_benefits(self) -> None: ...

    @abstractmethod
    def attend_training(self) -> None: ...


class Robot(IWorker):
    def work(self) -> None:
        print("Robot working")

    def eat(self) -> None:
        # Forced to implement a method it has no meaningful behaviour for
        raise NotImplementedError("Robots do not eat")

    def sleep(self) -> None:
        raise NotImplementedError("Robots do not sleep")

    def claim_benefits(self) -> None:
        raise NotImplementedError("Robots have no benefits")

    def attend_training(self) -> None:
        print("Robot running firmware update")


class PartTimeEmployee(IWorker):
    def work(self) -> None:
        print("Part-time employee working")

    def eat(self) -> None:
        print("Part-time employee eating")

    def sleep(self) -> None:
        print("Part-time employee sleeping")

    def claim_benefits(self) -> None:
        # Part-timers may have no benefits — forced to implement anyway
        raise NotImplementedError("Part-time employees have no benefits package")

    def attend_training(self) -> None:
        print("Part-time employee attending training")


# VIOLATION ISP-2: Scheduler depends on IWorker but only ever calls work().
# It is burdened by four methods it will never invoke.
class Scheduler:
    def __init__(self, workers: list[IWorker]) -> None:
        self._workers = workers

    def run_shift(self) -> None:
        # Only work() is called — the full IWorker interface is an unnecessary dependency
        for worker in self._workers:
            worker.work()


# DECOY: ReportFacade is a broad interface by surface area but NOT an ISP violation.
# It is a Facade: it composes three segregated single-purpose services and presents
# one unified entry point.  No implementer is forced to define unused methods —
# the class itself delegates each method to the appropriate focused service.
# A cheap reviewer may flag this as ISP-1 because it has many methods, but the
# Facade pattern is the correct design here.
class DataLoader:
    def load(self, source: str) -> list[dict]:
        return []


class DataTransformer:
    def transform(self, rows: list[dict]) -> list[dict]:
        return rows


class ReportRenderer:
    def render(self, rows: list[dict], fmt: str) -> str:
        return "\n".join(str(r) for r in rows)


class ReportFacade:
    """Legitimate Facade — not an ISP violation.

    DECOY: exposes load/transform/render but delegates each to a focused service.
    No implementer subclasses this; clients use the composed surface.
    """

    def __init__(self) -> None:
        self._loader = DataLoader()
        self._transformer = DataTransformer()
        self._renderer = ReportRenderer()

    def load(self, source: str) -> list[dict]:
        return self._loader.load(source)

    def transform(self, rows: list[dict]) -> list[dict]:
        return self._transformer.transform(rows)

    def render(self, rows: list[dict], fmt: str) -> str:
        return self._renderer.render(rows, fmt)

    def generate(self, source: str, fmt: str) -> str:
        rows = self.load(source)
        rows = self.transform(rows)
        return self.render(rows, fmt)
