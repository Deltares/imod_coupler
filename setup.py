import sys
from setuptools import find_namespace_packages, setup

__version__ = "0.1.0"
__name__ = "imod_coupler"
__author__ = "Deltares"

# ensure minimum version of Python is running
if sys.version_info[0:2] < (3, 6):
    raise RuntimeError("imod_coupler requires Python >= 3.6")


setup(
    name=__name__,
    description="The imod_coupler can be used to couple hydrologic kernels.",
    author=__author__,
    author_email="",
    url="https://github.com/Deltares/imod-coupler",
    license="AGPL",
    platforms="Windows, Mac OS-X, Linux",
    install_requires=["numpy"],
    packages=[__name__],
    include_package_data=find_namespace_packages(exclude=("tests", "examples")),
    version=__version__,
    classifiers=["Topic :: Scientific/Engineering :: Hydrology"],
    entry_points={"console_scripts": ["imodc = imod_coupler.__main__:main"]},
)
