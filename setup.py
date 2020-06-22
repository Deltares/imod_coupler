import sys
from setuptools import setup

__version__ = "0.1.0"
__name__ = "amipy"
__author__ = "Deltares"

# ensure minimum version of Python is running
if sys.version_info[0:2] < (3, 6):
    raise RuntimeError("imod-coupler requires Python >= 3.6")


setup(
    name=__name__,
    description="The imod-coupler can be usedto couple hydrologic kernels.",
    author=__author__,
    author_email="",
    url="https://github.com/Deltares/imod-coupler",
    license="AGPL",
    platforms="Windows, Mac OS-X, Linux",
    install_requires=["amipy"],
    packages=[__name__],
    include_package_data=True,
    version=__version__,
    classifiers=["Topic :: Scientific/Engineering :: Hydrology"],
)
