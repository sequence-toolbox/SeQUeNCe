# SeQUeNCe Documentation

This directory contains the documentation for the SeQUeNCe library.
This includes:

* Tutorials for the library modules
* References for available classes and methods

The documentation is built using the Sphinx documentation tool.
Tutorials are written in easily-modifiable markdown files.
References are generated automatically from source docstrings using the Sphinx `autodoc` module.

## Building HTML Pages

Sphinx can be easily installed via pip:

```
$ pip install -U sphinx
```

Once installed, the project can be built with the included makefile:

```
$ make html
```

The root file `index.html`, found under the builds directory, can then be opened.
