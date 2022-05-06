from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Driver(ABC):
    """Driver base class

    Inherit from this class when creating a new driver
    """

    def execute(self) -> None:
        """Execute the driver"""

        # This will initialize and couple the kernels
        self.initialize()

        # Run the time loop
        while self.get_current_time() < self.get_end_time():
            self.update()

        logger.info("New simulation terminated normally")

        self.finalize()

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the coupled models"""
        ...

    @abstractmethod
    def update(self) -> None:
        """Perform a single time step"""
        ...

    @abstractmethod
    def finalize(self) -> None:
        """Cleanup the resources"""
        ...

    @abstractmethod
    def get_current_time(self) -> float:
        """Return current time"""
        ...

    @abstractmethod
    def get_end_time(self) -> float:
        """Return end time"""
        ...

    @abstractmethod
    def report_timing_totals(self) -> None:
        """Report total time spent on coupling"""
        ...
