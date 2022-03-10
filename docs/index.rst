###########
iMOD Suite
###########

Introduction
------------

The iMOD Suite provides tools to efficiently build and visualize
groundwater models. 

Deltares is working to integrate and improve our groundwater software. 
Therefore iMOD is extended with a new iMOD Suite to link to the latest 
developments on the MODFLOW and on the changing requirements in the field 
of groundwatermodelling, most pressing currently the support 
of unstructured grids. 

We created the new iMOD Suite to aid pre- and post-processing
unstructured groundwater models. 
Furthermore, a second goal of this suite was to better connect to
the latest developments in the data science ecosystem, by utilizing:

* Existing data format conventions (NetCDF, UGRID) instead of 
  developing new ones, allowing more user flexibility to find the right
  tools for the right job.
* Widely used and tested software (QGIS) to which we add our extension, 
  instead of creating complete programs ourselves.
* Modern programming languages (C++ and Python) that 
  allow connecting to a big and lively software ecoystem.

The iMOD Suite offers different modules which support 
modelling with MODFLOW 6 (including unstructured meshes):

#. :doc:`iMOD Viewer <viewer_index>`: 
   The iMOD Viewer consist of a standalone 3D viewer and a QGIS plugin. The
   :doc:`iMOD QGIS Plugin <qgis_user_manual>` QGIS plugin allows visualisation
   of model input and output with tools for cross-sections, timeseries and link
   to the 3D viewer. It supports structured NetCDF, UGRID and IPF files. And the
   :doc:`iMOD 3D Viewer <3dviewer_user_manual>` for interactive 3D visualisation
   of unstructured input and output. Supports UGRID file format and IPF borelog
   files.
#. :doc:`iMOD Python <python_index>`:
   A Python package to support MODFLOW groundwater modeling. It makes it easy 
   to go from your raw data to a fully defined MODFLOW model, with the aim 
   to make this workflow reproducable.
#. :doc:`iMOD Coupler <coupler_index>`:
   Software that couples MODFLOW 6 to other computational cores. It currently
   supports a coupling to MetaSWAP, but additional computational cores are
   planned in the future.

.. figure:: screenshots/index/NHI-zz_cross-section.png

  Easy plotting of 4 dimensional [t, z, y, x] data in the iMOD QGIS plugin.
  The example shows the chlorine concentrations computed 
  by the `NHI fresh-salt model 
  <https://gitlab.com/deltares/imod/nhi-fresh-salt>`_.

.. figure:: screenshots/index/NHI-zz_3d_viewer.png

  The chlorine concentrations computed by the NHI-fresh-salt model
  for the province of Zeeland, plotted in the new iMOD 3D viewer. 
  The top layer is made partly transparent, 
  creating the pretty mist effect in the creek ridges.

Comparison with iMOD 5
----------------------

The proven technology and expertise of iMOD is consolidated within 
iMOD 5. iMOD 5 supports structured calculations with MODFLOW2005
and structured MODFLOW 6 and can be coupled to the unsaturated zone 
model MetaSWAP. 
The model input and output can be visualised in its fast interactive viewer. 
`The documentation of iMOD 5 can be found here 
<https://oss.deltares.nl/web/imod>`_
.

Important technological innovations will be developed 
in the new iMOD Suite, whereas iMOD 5 will be maintained the coming years, 
but will see no big new feature developments. 
:numref:`table_1` and :numref:`table_2` respectively provide comparisons
between iMOD Suite and iMOD 5 for the components and supported MODFLOW6 packages.

.. _table_1:

.. list-table:: Comparison between iMOD Suite & iMOD 5
  :header-rows: 1
  :stub-columns: 1

  * - 
    - iMOD Suite
    - iMOD 5
  * - computational kernels
    - MODFLOW 2005, MODFLOW 6, SEAWAT, MT3DMS
    - MODFLOW 2005, MODFLOW 6, SEAWAT, MT3DMS, MetaSWAP
  * - file types
    - NetCDF, UGRID, shp, tiff, idf, ipf, gen
    - idf, ipf, isg, gen
  * - grid types
    - structured & unstructured
    - structured & nested structured
  * - scripted pre-processing
    - iMOD Python
    - iMOD Batch
  * - interactive pre-processing
    - (QGIS)
    - iMOD GUI
  * - scripted 2D plot
    - iMOD Python
    - iMOD Batch
  * - interactive 2D plot
    - iMOD QGIS plugin (& QGIS)
    - iMOD GUI
  * - scripted 3D plot
    - iMOD Python
    -  
  * - interactive 3D plot
    - iMOD 3D Viewer
    - iMOD GUI

.. _table_2:

.. csv-table:: Supported MODFLOW6 flow packages in iMOD Suite & iMOD 5
   :file: tables/supported_packages.csv
   :widths: 15, 40, 20, 20
   :header-rows: 1

.. toctree::
   :hidden:

   viewer_index
   python_index
   coupler_index
   workflow_index
   further_links
