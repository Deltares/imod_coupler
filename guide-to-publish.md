# How to release in Github and publish to PyPi

- Remove the `-dev` suffix from the version number in `imod_coupler/__init__.py`

- Increase the version number in `imod_coupler/__init__.py`

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
