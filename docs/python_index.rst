***********
iMOD Python
***********

The iMOD Python package is designed to help you in your MODFLOW groundwater modeling efforts.
It makes it easy to go from your raw data to a fully defined MODFLOW model, with the aim to make this process reproducable.
Whether you want to build a simple 2D conceptual model, or a complex 3D regional model with millions of cells,
iMOD Python scales automatically by making use of `dask <https://dask.org/>`__.

By building on top of popular Python packages like `xarray <http://xarray.pydata.org/>`__, `pandas <http://pandas.pydata.org/>`__,
`rasterio <https://rasterio.readthedocs.io/en/latest/>`__ and `geopandas <http://geopandas.org/>`__, a lot of functionality comes
for free.

Currently we support the creation of the following MODFLOW-based models:

* `USGS MODFLOW 6 <https://www.usgs.gov/software/modflow-6-usgs-modular-hydrologic-model>`__, currently only the Groundwater Flow packages
* `iMODFLOW <https://oss.deltares.nl/web/imod>`__
* `iMOD-WQ <https://oss.deltares.nl/web/imod>`__, which integrates SEAWAT (density-dependent groundwater flow) and MT3DMS (multi-species reactive transport calculations)

Documentation: https://deltares.gitlab.io/imod/imod-python
This documentation includes a section "How do I" which can be used for common data conversions in imod-python or xarray. This section will be regular updated based
on the different questions of users. 

Source code: https://gitlab.com/deltares/imod/imod-python

.. toctree::
   :hidden:
   :numbered:

   python_install
   python_getting_started
