# How to release in Github and publish to PyPi

- Copy the TeamCity configuration "Testbench" and all its dependencies

- Set the version control sources of all dependencies to a suitable release and the one of imod_coupler to current main

- Remove the `-dev` suffix from the version number in `imod_coupler/__init__.py`

For example: `__version__ = "0.10.0-dev"` -> `__version__ = "0.10.0"`

- Increase the version number in `imod_coupler/__init__.py`

For example: `__version__ = "0.10.0"` -> `__version__ = "0.11.0"`

- Create a new commit with the updated version number,
and push to remote

- Create a new Github release
 
- If present remove build and dist folder

- Recursively remove all .egg-info files
On powershell you can do this with
```
rm -r *.egg-info
```
- If not done yet, install twine via
```
pip install build twine
```
- Re-create the wheels:
```
python -m build
```

- Check the package files:
```
twine check dist/*
```

- Re-upload the new files:
```
twine upload dist/*
```

- Add the `-dev` suffix to the version number in `imod_coupler/__init__.py`

For example: `__version__ = "0.11.0"` -> `__version__ = "0.11.0-dev"`

- Set the version control sources of the newly created TeamCity configurations to the current iMOD Coupler release
