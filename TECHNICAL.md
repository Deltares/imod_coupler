# Technical Reference
This document describes how MetaSWAP and MODFLOW6 are coupled. 
It is intended for groundwater modellers, who need to know which variables are exchanged between computational kernels and at which moment. 
For details of the inner workings of the code, we refer to the docstrings in the code.

Below is a flowchart showing the order in which one timestep is iteratively solved and when data is exchanged between MetaSWAP and MODFLOW6. 
The data exchange is done as follows. 
* When data is exchanged from MODFLOW to MetaSWAP, MODFLOW sets the head (i.e. "`hgwmodf`") in MetaSWAP. 
* When data is exhanged from  MetaSWAP to MODFLOW, MetaSWAP provides a recharge and sets the storage coefficient. 
Currently it sets the specific storage (for confined flow), to conform to the previous implementation of a MetaSWAP-MODFLOW coupling. 
A recharge package (RCH) is required in the MODFLOW6 model to facilitate the recharge flux of MetaSWAP.

![timestep](./figures/MF6BMI_coupling.png)