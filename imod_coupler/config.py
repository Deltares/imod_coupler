import logging
import os
import re
import sys
from typing import Any, List
import toml

from imod_coupler.errors import ConfigError

logger = logging.getLogger()


class Config(object):
    def __init__(self, filepath):
        """
        Args:
            filepath (str): Path to config file
        """
        if not os.path.isfile(filepath):
            raise ConfigError(f"Config file '{filepath}' does not exist")

        # Load in the config file at the given filepath
        self.data = toml.load(filepath)

        self.exchanges = self._get_cfg(["exchanges"])

        self.kernels = self.get_kernels()

        self.validate_kernel_paths()

    def validate_kernel_paths(self):
        for kernel in self.kernels:
            # Validate paths
            dll_path = self._get_cfg(["kernels", kernel, "dll"])
            if not os.path.exists(dll_path):
                raise ConfigError(
                    f"DLL path '{dll_path}' for '{kernel}' does not exist"
                )

            model_path = self._get_cfg(["kernels", kernel, "model"])
            if not os.path.isdir(model_path):
                raise ConfigError(
                    f"Model path '{model_path}' for '{kernel}' does not exist"
                )

            dependency_path = self._get_cfg(
                ["kernels", kernel, "dll_dependency"], required=False
            )
            if dependency_path:
                if not os.path.isdir(dependency_path):
                    raise ConfigError(
                        f"DDL dependency path '{dependency_path}' for '{kernel}' does not exist"
                    )

    def get_kernels(self):
        """Get kernels and check if they match up"""

        expected_kernels = set()
        for index, _ in enumerate(self.exchanges):
            expected_kernels.add(self._get_cfg(["exchanges", index, "kernel1"]))
            expected_kernels.add(self._get_cfg(["exchanges", index, "kernel2"]))

        kernels = set(self._get_cfg(["kernels"]).keys())
        missing_kernels = set.difference(expected_kernels, kernels)
        if missing_kernels:
            raise ConfigError(f"Kernel {', '.join(missing_kernels)} missing")

        return expected_kernels

    def _get_cfg(self, path, default=None, required=True):
        """Get a config option from a path and option name, specifying whether it is
        required.
        Raises:
            ConfigError: If required is specified and the object is not found
                (and there is no default value provided), this error will be raised
        """
        data = self.data
        # Sift through the the config until we reach our option
        for name in path:
            try:
                data = data[name]
            except KeyError:
                # Raise an error if it was required
                if required or not default:
                    raise ConfigError(f"Config option {'.'.join(path)} is required")

                # or return the default value
                return default

        # We found the option. Return it
        return data
