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

Base Config
-----------


+------------+----------------------------------------+
| log_level  |                                        |
+============+========================================+
| type       | string                                 |
+------------+----------------------------------------+
| default    | INFO                                   |
+------------+----------------------------------------+
| enum       | DEBUG, INFO, WARNING, ERROR, CRITICAL  |
+------------+----------------------------------------+



 =========== ========== 
  timing                
 =========== ========== 
  type        boolean   
  required    false     
  default     false     
 =========== ========== 

 
 ============== ========= 
  driver_type             
 ============== ========= 
  type           string   
  required       true     
  enum           metamod  
 ============== ========= 

driver
------

kernels
^^^^^^^

modflow6
""""""""

 =========== ========= 
  dll                  
 =========== ========= 
  type        string   
  required    true                           
 =========== ========= 

 ============== ========= 
  dll_dep_dir             
 ============== ========= 
  type           string   
  required       false    
 ============== ========= 

 =========== ========= 
  work_dir             
 =========== ========= 
  type        string   
  required    true     
 =========== ========= 



metaswap
""""""""

 =========== ========= 
  dll                  
 =========== ========= 
  type        string   
  required    true                           
 =========== ========= 

 ============== ========= 
  dll_dep_dir             
 ============== ========= 
  type           string   
  required       false    
 ============== ========= 

 =========== ========= 
  work_dir             
 =========== ========= 
  type        string   
  required    true     
 =========== ========= 




.. ## log_level

.. ## timing

.. ## driver_type

.. ## driver
