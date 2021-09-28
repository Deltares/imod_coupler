# How to release in github and publish to PyPi

1) If present remove build and dist folder

2) Recursively remove all .egg-info files
On powershell you can do this with
```
rm -r *.egg-info
```

3) If not done yet, install twine via
```
pip install twine
```
4) Update the version number in the `__init__.py` file

5) Make a new commit with the updated version number,
and push to remote

6) Make a new github release

7) Re-create the wheels:
```
python setup.py sdist bdist_wheel
```
8) Re-upload the new files:
```
twine upload dist/*
```
