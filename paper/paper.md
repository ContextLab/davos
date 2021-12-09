---
title: 'Davos: The Python package smuggler'
tags:
 - Python
 - Jupyter Notebook
 - JupyterLab
 - Google Colab
 - Reproducibility
 - package-management
 - import
 - install
 - pip
authors:
 - name: Paxton C. Fitzpatrick
   orcid: 0000-0003-0205-3088
   affiliation: 1
 - name: Jeremy R. Manning
   orcid: 0000-0001-7613-4732
   affiliation: 1
affiliations:
 - name: Department of Psychological and Brain Sciences, Dartmouth College
   index: 1
date: 16 November 2021
bibliography: paper.bib
link-citations: true
---


# Summary

`davos` is a Python package for managing dependencies at runtime. It allows users to specify requirements directly 
within their code that are validated and, if necessary, installed in a just-in-time fashion. `davos` was developed as a 
tool for turning standard Jupyter notebooks [@KluyEtal16] into self-contained, fully-specified Python environments to 
facilitate code sharing, collaboration, and reproducibility.

Importing `davos` enables an additional Python keyword: `smuggle`. The `smuggle` statement can be used as a drop-in 
replacement for the built-in `import` statement to load libraries, modules, and other objects into the current 
namespace. However, whereas `import` will fail if the requested package is not installed locally, `smuggle` statements 
can handle missing packages on the fly. If a smuggled package does not exist in the local environment, `davos` 
will install it, make its contents visible to Python's import machinery, and load it into the namespace for immediate 
use.

While the `smuggle` statement may simply be used on its own, `davos` defines an additional construct called the "*onion 
comment*" that provides greater control over its behavior and more complex functionality. An onion comment is a special 
type of inline comment that can be placed on a line containing a `smuggle` statement to customize how `davos` (1) 
determines whether the smuggled package should be installed, and (2) retrieves and installs the package, if necessary. 
Onion comments follow a simple syntax based on the type comment syntax introduced in PEP 484 [@vanREtal14], and are 
designed to make controlling installation via `davos` intuitive and familiar&mdash;simply specify the installer program 
(e.g., `pip`) and provide the same arguments one would use to install the package manually via the command line:

```python
import davos

# if numpy is not installed locally, pip-install it with verbose output
smuggle numpy as np    # pip: numpy --verbose 

# install pandas without checking for an existing local version first
smuggle pandas as pd    # pip: pandas --ignore-installed

# install scipy from a relative local path, in editable mode
from scipy.interpolate smuggle interp1d    # pip: -e ../../pkgs/scipy
```

Onion comments are also useful when smuggling a package whose distribution name (i.e., the name used when installing it) 
is different from its top-level module name (i.e., the name used when importing it):

```python
smuggle dateutil    # pip: python-dateutil
from sklearn.decomposition smuggle pca    # pip: scikit-learn
```

However, the most powerful use of the onion comment is making `smuggle` statements *version-sensitive*. Adding a 
[version specifier](https://www.python.org/dev/peps/pep-0440/#version-specifiers) to an onion comment tells `davos` that 
an existing installation of the smuggled package should be used only if its version satisfies the given constraint; 
otherwise, a suitable version should be installed:

```python
# use matplotlib v3.4.2 specifically, pip-installing it if needed
smuggle matplotlib.pyplot as plt    # pip: matplotlib==3.4.2

# use a version of seaborn no older than v0.9.1, but prior to v0.11
smuggle seaborn as sns    # pip: seaborn>=0.9.1,<0.11
```

This also works with specific VCS reference (e.g., git branch, commit, tag, etc.):

```python
# use quail as it existed on GitHub at commit 6c847a4
smuggle quail    # pip: git+https://github.com/ContextLab/quail.git@6c847a4
```

Because onion comments can be used to make `smuggle` statements version-sensitive, `davos` provides a powerful way of
creating fully contained shareable workflows within a single iPython notebook.  In some cases, this can obviate the need
for constructing containerized or virtualized environments (e.g., using [Docker](https://www.docker.com/), [Singularity](https://sylabs.io/singularity/), or [conda](https://docs.conda.io/en/latest/)).

For example, `davos` enables users to specify specific package versions (and even specific VCS revisions, such as git commit
hashes) of to-be-smuggled packages.  When `smuggle` statements are called multiple times within the same notebook (e.g., with
different onion comments), multiple versions of the same package may be used within a single interpreter session.  Although
the current version of `davos` is already fully usable and feature-complete, future extensions of the package could enable
use of the `smuggle` keyword within "vanilla" (non-interactive) Python scripts, and/or support of alternative package managers
such as `conda`.

# Statement of Need

Modern open science practices often entail sharing code and data to enable scientists to reproduce and extend each others' work.
As of the time of writing, Python is already one of the most widely used scientific programming languages, and its user base
is expanding rapidly.  A centerpiece of the Python ecosystem is a powerful and extensive data science toolkit designed to facilitate
rapid development and collaboration.  These tools include platforms for interactive development (e.g., Project 
Jupyter [@PereGran07;@KluyEtal16] and Google Colaboratory), packages for data manipulation (e.g., `NumPy` [@HarrEtal20], 
`SciPy` [@VirtEtal20], `Pandas` [@McKi10]),  packages for data visualization (e.g., `Matplotlib` [@Hunt07], `seaborn` [@Wask21]), and
myriad others.

One downside of the rapidly growing Python ecosystem is that different versions of the same software package can behave differently
as syntax changes are introduced, bugs are introduced or fixed, features are implemented or removed, support for different versions of
Python is added or dropped, and so on.  This instability can be at odds with the goal of producing reproducible workflows that remain
usable across different development environments and over time.  Through its `smuggle` keyword and onion comments, the `davos` package
improves the stability of Python-based workflows by providing a convenient means of precisely controling and manipulating the environment
in which specific code is executed.

# References
