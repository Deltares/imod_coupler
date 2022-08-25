Technical Reference
===================

General description
-------------------

This document describes how MetaSWAP and MODFLOW6 are coupled. It is
intended for groundwater modellers, who need to know which variables are
exchanged between computational kernels and at which moment. For details
of the inner workings of the code, we refer to the docstrings in the
code.

Below is a flowchart showing the order in which one timestep is
iteratively solved and when data is exchanged between MetaSWAP and
MODFLOW6. The data exchange is done as follows.

-  When data is exchanged from MODFLOW to MetaSWAP, MODFLOW sets the
   head (i.e. "``hgwmodf``") in MetaSWAP.
-  When data is exhanged from MetaSWAP to MODFLOW, MetaSWAP provides a recharge,
   sets the storage, and extracts groundwater from deeper layers for sprinkling
   (if switched on). 

.. image:: ./figures/MF6BMI_coupling.png
   :align: center


Requirements
------------

Currently only confined flow is supported, similar to a previous implementation
of MetaSWAP-MODFLOW coupling. Both the specific storage and the storage
coefficient option of Modflow 6 are supported. A recharge package (RCH) is
required in the MODFLOW6 model to facilitate the recharge flux of MetaSWAP.
Furthermore, a well package (WEL) is required to facilitate the extraction of
groundwater for MetaSWAP's sprinkling.

Files
=====

The following files are required to couple the two model codes. These
files provide the mappings from MODFLOW indices to the MetaSWAP svats.

MetaSWAP requires the file:

-  ``mod2svat.inp``

Modflow6 requires the files:

-  ``[filename].rch``
-  ``[filename].wel`` (optional)

The coupler itself requires the following files:

-  ``nodenr2svat.dxc``
-  ``rchindex2svat.dxc``
-  ``wellindex2svat.dxc`` (optional)

Below we will describe the format for each file.

MetaSWAP
--------

mod2svat.inp
~~~~~~~~~~~~

The file format for this file is also described in the `SIMGRO IO
manual <ftp://ftp.wur.nl/simgro/doc/Report_913_3_V8_0_0_7.pdf>`__. It is
as follows:

::

   node_nr svat ly
   ...

Were ``node_nr`` is the MODFLOW6 node number (to be specific: the user
node number), which which replaces the MODFLOW 2005 CellID. ``svat`` is
the MetaSWAP svat number and ``ly`` is the Modflow layer number. Note
that the format for this file should be fixed to

.. code:: python

   f"{nodenr:10d}  {svat:10d}{ly:2d}"

where the number behind the colon indicates the number of characters,
padded with whitespace. Note the two whitespaces between ``nodenr`` and
``svat``.

Modflow6
--------

[filename].rch
~~~~~~~~~~~~~~

A dummy recharge file, of which the fluxes will be overrided. The
location of the recharge cells is used to assign an recharge index by
Modflow6. The file format of the .rch file is described
`here <https://modflow6.readthedocs.io/en/latest/_mf6io/gwf-rch.html>`__.
To specify an uncoupled recharge as well, a second RCH package should be
defined. How to define a second stress package is explained
`here <#how-to-define-a-second-stress-package-for-modflow6>`__. Please
note that in the model name file the `package
name <https://modflow6.readthedocs.io/en/latest/_mf6io/gwf-nam.html#block-packages>`__
should correspond to the package name specified :ref:`in the configuration file
<configuration_file>`.

[filename].wel
~~~~~~~~~~~~~~

A dummy well file, of which the fluxes will be overrided. The location of the
wells is used to assign a well index by Modflow6. The file format of the .wel
file is described `here
<https://modflow6.readthedocs.io/en/latest/_mf6io/gwf-wel.html>`__. To specify
uncoupled extractions/injections as well, a second WEL package should be
defined. How to define a second stress package is explained `here
<#how-to-define-a-second-stress-package-for-modflow6>`__. Please note that the
`package name in the model name file
<https://modflow6.readthedocs.io/en/latest/_mf6io/gwf-nam.html#block-packages>`__
should correspond to the package name specified :ref:`in the configuration file
<configuration_file>`.

Coupler
-------

nodenr2svat.dxc
~~~~~~~~~~~~~~~

This file takes care of mapping the MODFLOW node numbers to the MetaSWAP
svats, which is required for coupling the heads and storages of both
kernels, it thus excludes nodes connected where wells are for
sprinkling. The file format is as follows:

::

   node_nr svat ly
   ...

Where ``node_nr`` is the MODFLOW6 node number (to be specific: the user
node number), which replaces the MODFLOW 2005 CellID. ``svat`` is the
MetaSWAP svat number and ``ly`` is the Modflow layer number.

rchindex2svat.dxc
~~~~~~~~~~~~~~~~~

This file takes care of mapping the recharge cells to the MetaSWAP
svats. The file format is as follows:

::

   rch_index svat ly
   ...

Where ``rch_index`` is the MODFLOW6 RCH index number, which equals the
row number of the data specified under ``period`` in the ``.rch`` file.
``svat`` is the MetaSWAP svat number and ``ly`` is the Modflow layer
number.

wellindex2svat.dxc
~~~~~~~~~~~~~~~~~~

This file takes care of mapping MODFLOW wells to the MetaSWAP svats for
sprinkling. The file format is as follows:

::

   well_index svat ly
   ...

Where ``well_index`` is the MODFLOW6 WEL index number, which equals the
row number of the data specified under ``period`` in the ``.wel`` file.
``svat`` is the MetaSWAP svat number and ``ly`` is the Modflow layer
number.

How to define a second stress package for Modflow6
--------------------------------------------------

A second stress package (in our case named ``WELL2``) can be defined in
the flow model's ``.nam`` file (GWF_1.nam).

::

   begin options
   end options

   begin packages
     dis6 GWF_1/dis.dis
     chd6 GWF_1/chd.chd
     npf6 GWF_1/npf.npf
     ic6 GWF_1/ic.ic
     wel6 GWF_1/wel.wel WELLS_MSW
     wel6 GWF_1/wel2.wel WELL2
     sto6 GWF_1/sto.sto
     oc6 GWF_1/oc.oc
   end packages

The argument values ``WELLS_MSW`` and ``WELL2``, specify the packagenames to be
printed in the water budget .lst file. :ref:`In the configuration file
<configuration_file>` you have to specify which packagename is used for the
coupling.

