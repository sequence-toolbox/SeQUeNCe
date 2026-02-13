# SeQUeNCe Documentation

This directory contains the documentation for the SeQUeNCe library.
This includes:

* Tutorials for the library modules
* References for available classes and methods

The documentation is built using the Sphinx documentation tool.
Tutorials are written in easily-modifiable markdown files.
Reference pages use Sphinx `autodoc` to pull API documentation from source docstrings.
Reference `.rst` stub files are generated from the source tree with `make apidoc`.

## Read the Docs Build (Remote)

Documentation publishing is handled remotely by Read the Docs (RTD) from this repository.
RTD runs `make apidoc` before the Sphinx build so reference stubs are regenerated automatically.

## Local Preview (Optional)

Sphinx and recommonmark can be easily installed via pip:

```
$ pip install -U sphinx
$ pip install recommonmark
```

Once installed, you can preview docs locally with:

```
$ make apidoc
$ make html
```

The root file `index.html`, found under the builds directory, can then be opened.

NOTE: there might be a discrepancy between the remote Read the Docs and the doc files (.rst) in the repository.
To resolve the discrepancy, run `make apidoc` and commit the change.