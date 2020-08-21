from dataclasses import dataclass


@dataclass
class Kernel:
    """Class for maintaining kernel data."""

    dll: str
    model: str
    dll_dependency: str
