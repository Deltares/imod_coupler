.. _configuration_file:

Configuration file
------------------

The configuration file is necessary to describe the model and its
dependencies. It is in the `toml <https://toml.io/en/>`__ format and
should have a ``.toml`` extension.

Note that ``toml`` uses quote marks differently than ``python``. Single
quotes in toml (``''``) are interpreted similarly to how python would
interpret a rawstring (``r''`` or ``r""``), whereas double quotes
(``""``) are interpreted in a similar manner to regular strings in
python (``""`` or ``''``). This matters for paths on Windows, for which
we advice to use single quotes.

.. code:: toml

   # This is a configuration file for the imod_coupler
   # Relative paths are interpreted as relative to the configuration file path

   [kernels]
       [kernels.modflow6]
       dll = '/path/to/libmf6.dll'
       model = '.'

       [kernels.metaswap]
       dll = '/path/to/MetaSWAP.dll'
       model = './GWF_1/MSWAPINPUT'
       dll_dependency = '/path/to/MPICHDLL'


   [[exchanges]]
   # Two kernels per exchange
   kernels = ['modflow6', 'metaswap']
