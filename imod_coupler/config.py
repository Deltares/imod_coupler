import logging
import os
import re
import sys
from typing import Any, List

import toml

from imod_coupler.errors import ConfigError
from imod_coupler.utils import cd
from imod_coupler.kernel import Kernel

logger = logging.getLogger()


class Config(object):
    def __init__(self, filepath):
        """
        Args:
            filepath (str): Path to config file
        """
        if not os.path.isfile(filepath):
            raise ConfigError(f"Config file '{filepath}' does not exist")

        with cd(os.path.dirname(filepath)):
            # Load in the config file at the given filepath
            self.data = toml.load(filepath)
            self.filepath = filepath

            self.exchanges = self._get_cfg(["exchanges"])

            kernels = self.get_kernel_set()

            self.get_kernel_data(kernels)

    def get_kernel_set(self):
        """Get kernels and check if they match up"""

        expected_kernels = set()
        for index, _ in enumerate(self.exchanges):
            kernels = self._get_cfg(["exchanges", index, "kernels"])
            for kernel in kernels:
                expected_kernels.add(kernel)

        kernels = set(self._get_cfg(["kernels"]).keys())
        missing_kernels = set.difference(expected_kernels, kernels)
        if missing_kernels:
            raise ConfigError(f"Kernel {', '.join(missing_kernels)} missing")

        return expected_kernels

    def get_kernel_data(self, kernels):
        self.kernels = {}
        for kernel in kernels:
            # Validate paths
            dll = self._get_cfg(["kernels", kernel, "dll"])
            if not os.path.exists(dll):
                raise ConfigError(f"DLL path '{dll}' for '{kernel}' does not exist")
            else:
                dll = os.path.abspath(dll)

            model = self._get_cfg(["kernels", kernel, "model"])
            if not os.path.isdir(model):
                raise ConfigError(f"Model path '{model}' for '{kernel}' does not exist")
            else:
                model = os.path.abspath(model)

            dll_dependency = self._get_cfg(
                ["kernels", kernel, "dll_dependency"], required=False
            )
            if dll_dependency:
                if not os.path.isdir(dll_dependency):
                    raise ConfigError(
                        f"DLL dependency path '{dll_dependency}'"
                        f"for '{kernel}' does not exist"
                    )
                else:
                    dll_dependency = os.path.abspath(dll_dependency)

            self.kernels[kernel] = Kernel(dll, model, dll_dependency)

    def _get_cfg(self, path, default=None, required=True):
        """Get a config option from a path and option name, specifying whether it is
        required.
        It also checks for environment variables used to override the config path.

        Raises:
            ConfigError: If required is specified and the object is not found
                (and there is no default value provided), this error will be raised
        """

        # Create the environment variable string
        # e.g. IMODC__KERNELS__MODFLOW6__DLL
        env_variable = "IMODC"
        for name in path:
            env_variable = env_variable + "__" + str(name)

        # Check if an environment variable is set to override the config file
        value = os.environ.get(env_variable)
        if value:
            return value

        value = self.data
        # Sift through the the config until we reach our option
        for name in path:
            try:
                value = value[name]
            except KeyError:
                # Raise an error if it was required
                if required:
                    raise ConfigError(f"Config option {'.'.join(path)} is required")

                # or return the default value
                return default

        # We found the option. Return it
        return value
