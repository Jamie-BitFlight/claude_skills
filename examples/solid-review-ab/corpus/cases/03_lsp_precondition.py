# CASE: LSP violations — precondition strengthening (LSP-1), NotImplementedError (LSP-2),
# silent no-op override (LSP-3).
# SYSTEMATIC MISS (LSP-1 subtle): DiscountedAccount.withdraw strengthens the precondition
# hidden behind what LOOKS like input validation. The base class accepts any positive amount;
# the override adds a minimum-balance constraint that the base contract does not declare.
# Cheap models typically flag the obvious NotImplementedError but miss this subtler case.
from __future__ import annotations

from abc import ABC, abstractmethod


class BankAccount(ABC):
    """Abstract bank account — base contract."""

    def __init__(self, balance: float) -> None:
        self._balance = balance

    @abstractmethod
    def deposit(self, amount: float) -> None:
        """Deposit amount into the account.

        Precondition: amount > 0
        Postcondition: self._balance increased by amount
        """
        ...

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        """Withdraw amount from the account.

        Precondition: amount > 0
        Postcondition: returns True and self._balance reduced, or returns False
        """
        ...

    @property
    def balance(self) -> float:
        return self._balance


class StandardAccount(BankAccount):
    """Standard account — faithful implementation of the base contract."""

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._balance += amount

    def withdraw(self, amount: float) -> bool:
        if amount <= 0 or amount > self._balance:
            return False
        self._balance -= amount
        return True


# SYSTEMATIC MISS — LSP-1 (subtle precondition strengthening):
# DiscountedAccount.withdraw adds a minimum_balance constraint that the base contract
# does not declare. A caller holding a BankAccount reference cannot know that this
# subtype will refuse a valid withdrawal that StandardAccount would accept.
# The constraint is hidden inside a comment-free validation block that LOOKS
# like a sane guard — cheap models miss this.
class DiscountedAccount(BankAccount):
    """Account with a minimum balance requirement — strengthens the withdraw precondition."""

    MINIMUM_BALANCE = 50.0

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._balance += amount

    def withdraw(self, amount: float) -> bool:
        # Strengthened precondition: balance after withdrawal must remain >= MINIMUM_BALANCE.
        # Base contract only requires amount > 0 and amount <= balance.
        # This is invisible to callers substituting BankAccount with DiscountedAccount.
        if self._balance - amount < self.MINIMUM_BALANCE:
            return False
        self._balance -= amount
        return True


# VIOLATION LSP-2: SavingsAccount.deposit raises NotImplementedError,
# changing the base contract for a method that must be defined.
class SavingsAccount(BankAccount):
    """Savings account that rejects deposits — breaks the base contract."""

    def deposit(self, amount: float) -> None:
        # Raises NotImplementedError: subtype is not substitutable for BankAccount
        # in any context that calls deposit().
        raise NotImplementedError("SavingsAccount does not accept deposits via this method")

    def withdraw(self, amount: float) -> bool:
        if amount <= 0 or amount > self._balance:
            return False
        self._balance -= amount
        return True


# VIOLATION LSP-3: FrozenAccount.withdraw silently does nothing and always returns True,
# rejecting inputs the base accepts (any positive amount up to balance).
class FrozenAccount(BankAccount):
    """Frozen account that silently refuses all withdrawals."""

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._balance += amount

    def withdraw(self, amount: float) -> bool:
        # Silent no-op: always returns True but never deducts anything.
        # Violates the postcondition: self._balance is not reduced.
        return True
