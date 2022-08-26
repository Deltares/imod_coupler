.. _configuration_file:

Configuration file
==================

The configuration file is necessary to describe the model and its
dependencies. It is in the `toml <https://toml.io/en/>`__ format and
should have a ``.toml`` extension.

Note that ``toml`` uses quote marks differently than ``python``. Single
quotes in toml (``''``) are interpreted similarly to how python would
interpret a rawstring (``r''`` or ``r""``), whereas double quotes
(``""``) are interpreted in a similar manner to regular strings in
python (``""`` or ``''``). This matters for paths on Windows, for which
we advice to use single quotes.

.. literalinclude:: config/metamod.toml
    :language: toml

Config schema
-------------

.. csv-table:: log_level
    :widths: 3, 7

    description, "This setting determines the severity and therefore the verbosity of the log messages."
    type, string
    required, false
    default, INFO
    enum, "DEBUG, INFO, WARNING, ERROR, CRITICAL"

.. csv-table:: timing
    :widths: 3, 7

    description, "Specifies whether the coupling should be timed. This option requires the log level to at least include INFO."
    type, boolean
    required, false
    default, false

.. csv-table:: driver_type
    :widths: 3, 7

    description, "Specifies which driver should be used. Typically, this determines which hydrological kernels are coupled."
    type, string
    required, true
    enum, metamod


driver
------

kernels
^^^^^^^

modflow6
""""""""

.. csv-table:: dll
    :widths: 3, 7

    description, "The path to the MODFLOW 6 library."
    type, string
    required, true

.. csv-table:: dll_dep_dir
    :widths: 3, 7

    description, "The path to the dependencies of MODFLOW 6."
    type, string
    required, false

.. csv-table:: work_dir
    :widths: 3, 7

    description, "The working directory MODFLOW 6 expects. This is the directory where the simulation name file resides."
    type, string
    required, true


metaswap
""""""""

.. csv-table:: dll
    :widths: 3, 7

    description, "The path to the MetaSWAP library."
    type, string
    required, true

.. csv-table:: dll_dep_dir
    :widths: 3, 7

    description, "The path to the dependencies of MetaSWAP."
    type, string
    required, false

.. csv-table:: work_dir
    :widths: 3, 7

    description, "The working directory MetaSWAP expects."
    type, string
    required, true

coupling
^^^^^^^^

.. csv-table:: enable_sprinkling
    :widths: 3, 7

    description, "Whether to enable sprinkling, that is: enable extracting groundwater for irrigation."
    type, boolean
    required, true

.. csv-table:: mf6_model
    :widths: 3, 7

    description, "Specifies the MODFLOW 6 model name to which MetaSWAP will be coupled."
    type, string
    required, true


.. csv-table:: mf6_msw_recharge_pkg
    :widths: 3, 7

    description, "Specifies the package name (specified in the Modflow 6 simulation name file) of the recharge package to which MetaSWAP will be coupled."
    type, string
    required, true

.. csv-table:: mf6_msw_well_pkg
    :widths: 3, 7

    description, "Specifies the package name (specified in the Modflow 6 simulation name file) of the recharge package to which MetaSWAP will be coupled. This setting is only required if ``enable_sprinkling`` is set to ``true``."
    type, string
    required, false

.. csv-table:: mf6_msw_node_map
    :widths: 3, 7

    description, "Path to the file specifying the mapping between MODFLOW 6 cells and MetaSWAP svats."
    type, string
    required, true

.. csv-table:: mf6_msw_recharge_map
    :widths: 3, 7

    description, "Path to the file specifying the mapping between MODFLOW 6 recharge cells and MetaSWAP svats."
    type, string
    required, true

.. csv-table:: mf6_msw_recharge_map
    :widths: 3, 7

    description, "Path to the file specifying the mapping between MODFLOW 6 wells and MetaSWAP svats. This setting is only required if ``enable_sprinkling`` is set to ``true``."
    type, string
    required, false
