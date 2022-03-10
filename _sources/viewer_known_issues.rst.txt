
*************
Known Issues
*************

.. _plot_axis_off:

QGIS plugin
###########

Plot axis off
-------------

In the QGIS plugin, 
a weird offset in the plot axis can occur when you use a multiple monitor setup.
Both the Time series widget as well as the Cross-section widget can suffer from this.

.. figure:: screenshots/qgis_issues/plot_axis_offset.png

    Notice the y-axis being moved too high and 
    the x-axis being scaled weirdly.

So far we haven't been able to fix it in the code, 
so you can fix this as a user by either:

- Moving your QGIS application to the **main window** of your monitor setup
- In Windows, navigate to *Settings > Display* then under 
  *Rearrange your displays* select the monitor you want to view QGIS on, 
  and finally tick the box *Make this my main display*

..
  Technical comment:
  This is due to a bug in PyQtgraph, which is difficult to fix.
  The proposed fix of PyQtgraph requires us to run specific python code before 
  the application starts, which is impossible to do for a plugin.
  https://pyqtgraph.readthedocs.io/en/latest/how_to_use.html#hidpi-displays
  Qt6 has better support for multiple monitor setups, so when QGIS migrates
  to Qt6, this shouldn't be an issue anymore.

IPF reader does not support all IPF files
-----------------------------------------

Currently the IPF reader is not able to read every IPF file, 
as iMOD 5 supports quite a wide range of IPF files.
For example, iMOD 5 supports both whitespace and comma seperated files, 
whereas the QGIS plugin only supports comma seperated IPF files.
If the plugin is unable to read your IPF file, 
it is best to 
`read the file with iMOD Python <https://deltares.gitlab.io/imod/imod-python/api/generated/io/imod.ipf.read.html>`_ 
and consequently 
`write it again <https://deltares.gitlab.io/imod/imod-python/api/generated/io/imod.ipf.write.html>`_. 
This can help, because the IPF reader in iMOD Python 
is a lot more flexible, but its writer always writes
to a specific format. 
We plan to improve the flexibility of the plugin's IPF reader.

3D Viewer
#########

MSVCR100.dll missing
--------------------

You might get an error at startup of the 3D viewer, such as:
*"The code execution cannot proceed because MSVCR100.dll was not found. 
Reinstalling the progam may fix the problem"*

This usually happens on a clean machine, which has not yet installed the 
Microsoft Visual C++ 2010 redistributable. 
`You can download it here <https://www.microsoft.com/en-us/download/details.aspx?id=26999>`_

Make sure to check if you have a 32-bit or 64-bit Windows version on your 
system and consequently installing the right version of the redistributable. 
You can find this out pressing the Windows key (or clicking *Start*) and typing
*System Information*. Click it, and look under *"System Type"*. If it says
*x64-based PC*, you have a 64-bit system. 
