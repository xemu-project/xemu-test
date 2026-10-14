"""Exceptions raised by the xemu test harness."""


class XemuTestError(Exception):
    """Base class for harness errors."""


class RunNotImplementedError(XemuTestError, NotImplementedError):
    """A test subclass did not implement ``_run``."""

    def __init__(self) -> None:
        super().__init__("Subclass must implement run() method")


class HddSizeMismatchError(XemuTestError, FileExistsError):
    """An existing HDD image does not have the expected size."""

    def __init__(self) -> None:
        super().__init__("Target image path exists and is not expected size")


class XemuWindowNotFoundError(XemuTestError):
    """The main xemu window could not be located."""

    def __init__(self) -> None:
        super().__init__("Failed to find main xemu window...")
