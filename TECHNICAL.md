# Technical Reference

## General description

This document describes how MetaSWAP and MODFLOW6 are coupled. 
It is intended for groundwater modellers, who need to know which variables are exchanged between computational kernels and at which moment. 
For details of the inner workings of the code, we refer to the docstrings in the code.

Below is a flowchart showing the order in which one timestep is iteratively solved and when data is exchanged between MetaSWAP and MODFLOW6. 
The data exchange is done as follows. 
* When data is exchanged from MODFLOW to MetaSWAP, MODFLOW sets the head (i.e. "`hgwmodf`") in MetaSWAP. 
* When data is exhanged from  MetaSWAP to MODFLOW, MetaSWAP provides a recharge, sets the storage coefficient, and extracts groundwater from deeper layers for sprinkling (if switched on).
Currently it sets the specific storage (for confined flow), to conform to the previous implementation of a MetaSWAP-MODFLOW coupling. 
A recharge package (RCH) is required in the MODFLOW6 model to facilitate the recharge flux of MetaSWAP. 
Furthermore, a well package (WEL) is required to facilitate the extraction of groundwater for MetaSWAP's sprinkling. 

![timestep](./figures/MF6BMI_coupling.png)

# Files
The following files are required to couple the two model codes. 
These files provide the mappings from modflow indices to the MetaSWAP svats.

MetaSWAP requires the file:
* `mod2svat.inp`

Modflow6 requires the files
* `[filename].rch`
* `[filename].wel`

The coupler itsself requires the following files:
* `wellindex2svat.dxc`  
* `rchindex2svat.dxc`
* `nodenr2svat.dxc`

Below we will describe the format for each file.

## MetaSWAP
### mod2svat.inp
The file format for this file is also described in the [MetaSWAP IO manual](ftp://ftp.wur.nl/simgro/doc/Report_913_3_V8_0_0_7.pdf). It is as follows:

```
id svat ly
```

Where `id` is an index which can be the `node_nr` or `well_index` depending on whether `ly` equals 1 or is greater than 1, respectively. 
`svat` is the MetaSWAP svat number and `ly` is the Modflow layer number.

## Modflow6
### [filename].wel
A dummy well file, of which the fluxes will be overrided. To specify uncoupled extractions/injections, a second WEL package should be defined.

### [filename].rch
A dummy recharge file, of which the fluxes will be overrided. To specify a fixed recharge, a second RCH package should be defined. 

## Coupler
### wellindex2svat.dxc
This file takes care of coupling the wells to the MetaSWAP svats. The file format is as follows:

```
well_index svat ly
```

Where `well_index` is the MODFLOW6 WEL index number, which equals the row number of the data specified under `period` in the `.wel` file. 
`svat` is the MetaSWAP svat number and `ly` is the Modflow layer number.

### rchindex2svat.dxc
The file format is as follows:

```
rch_index svat ly
```

Where `rch_index` is the MODFLOW6 RCH index number, which equals the row number of the data specified under `period` in the `.rch` file. 
`svat` is the MetaSWAP svat number and `ly` is the Modflow layer number.

### nodenr2svat.dxc
The file format is as follows:

```
node_nr svat ly
```

Where `node_nr` is the MODFLOW6 node number (to be specific: the user node number), which replaces the MODFLOW 2005 CellID. 
`svat` is the MetaSWAP svat number and `ly` is the Modflow layer number.

## How to define a second stress package for Modflow6
A second stress package can be defined in the flow model's `.nam` file (GWF_1.nam).

```
begin options
end options

begin packages
  dis6 GWF_1/dis.dis
  chd6 GWF_1/chd.chd
  npf6 GWF_1/npf.npf
  ic6 GWF_1/ic.ic
  wel6 GWF_1/wel.wel wel1
  wel6 GWF_1/wel2.wel wel2
  sto6 GWF_1/sto.sto
  oc6 GWF_1/oc.oc
end packages
```
The optional argument values "wel1" and "wel2", specify the packagenames to be printed in the water budget .lst file.