# Development

## Publishing the package

### Publishing manually

In order to publish PyAstroSALT from your machine, first install twine, if you haven't done so already:

```shell
pipx install twine
```

Then remove the `dist` folder if need be:

```shell
rm -r dist
```

Build the package:

```shell
pyproject-build --sdist
```

If you have your own PyPI server, say `https://pypi.example.com`, create a file `.pypirc` in your home directory with the following content:

```
[distutils]
index-servers =
pypi
testpypi
example

[pypi]
repository = https://upload.pypi.org/legacy/

[testpypi]
repository = https://test.pypi.org/legacy/

[example]
repository = https://pypi.example.com/
```

You can then use twine to upload the package:

```shell
twine upload -r https://pypi.example.com dist/*
```

Afterwards you can install PyAstroSALT from your PyPI server:

```shell
python -m pip install --index-url https://pypi.example.com/
```

Upload the package to [Test PyPI](https://packaging.python.org/guides/using-testpypi/):

```shell
twine upload -r testpypi dist/*
```

You can then install PyAstroSALT from Test PyPI:

```shell
python -m pip install --extra-index-url https://test.pypi.org/simple/ pyastrosalt
```

```{warning}
TestPyPI lets you copy a command for installing the package. However, this uses `--index-url` instead of `--extra-index-url` and gives an error because setuptools cannot be found on TestPyPI.
```

If all looks good, you can publish your package:

```shell
twine upload dist/*
```
