"""Custom exceptions for the irp package."""

from __future__ import annotations


class IRPError(Exception):
    """Base exception for all errors raised by the irp framework."""

    pass


class PhysicsViolationError(IRPError):
    """Raised when an operation violates power flow physics or Kirchhoff's laws."""

    pass


class TopologyError(IRPError):
    """Raised when grid network topology is disconnected, malformed, or invalid."""

    pass


class InfeasibleModelError(IRPError):
    """Raised when an optimization problem is primal or dual infeasible."""

    pass


class CapacityDeficitError(IRPError):
    """Raised when available capacity fails to meet the Planning Reserve Margin."""

    pass
