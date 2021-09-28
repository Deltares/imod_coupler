# How to release in github and publish to PyPi

1) Update the version number in the `__init__.py` file

2) Make a new commit with the updated version number,
and push to remote

3) Make a new github release
 
4) If present remove build and dist folder

5) Recursively remove all .egg-info files
On powershell you can do this with
```
rm -r *.egg-info
```
6) If not done yet, install twine via
```
pip install twine
```
7) Re-create the wheels:
```
python setup.py sdist bdist_wheel
```
8) Re-upload the new files:
```
twine upload dist/*
```
