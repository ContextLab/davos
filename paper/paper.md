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

`davos` is a Python package for creating self-managing, reproducible workflows that specify dependencies directly within 
their code and install packages as needed at runtime. `davos` was developed to simplify sharing research-related code 
including data analyses, tutorials, and demos by allowing users to distribute their code and environment together in a 
single, ready-to-run Jupyter notebook [@KluyEtal16].

Importing `davos` enables an additional Python keyword: `smuggle`. The `smuggle` statement can be used as a drop-in 
replacement for the built-in `import` statement to load libraries, modules, and other objects into the current 
namespace. However, whereas `import` will fail if the requested package is not installed locally, `smuggle` statements 
can handle missing packages on the fly. If a smuggled package does not exist in the local environment, `davos` 
will install it, make its contents visible to Python's import machinery, and load it into the namespace for immediate 
use.

While the `smuggle` statement may simply be used on its own, `davos` defines an additional construct called the "*onion 
comment*" that provides greater control over its behavior as well as more complex functionality. An onion comment is a 
special type of inline comment that can be placed on a line containing a `smuggle` statement to customize how `davos` 
(1) determines whether the smuggled package should be installed, and (2) retrieves and installs the package, if 
necessary. Onion comments follow a simple syntax based on the type comment syntax introduced in PEP 484 [@vanREtal14], 
and are designed to make controlling installation via `davos` intuitive and familiar&mdash;simply specify the installer 
program (e.g., `pip`) and provide the same arguments one would use to install the package manually via the command line:

```python
import davos

# if numpy is not installed locally, pip-install it with verbose output
smuggle numpy as np    # pip: numpy --verbose 

# pip-install pandas without using or writing to the package cache
smuggle pandas as pd    # pip: pandas --no-cache-dir

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
[version specifier](https://www.python.org/dev/peps/pep-0440/#version-specifiers) to an onion comment will cause `davos`
to first search for the smuggled package in the local environment (as usual), but before loading it, also check that the 
installed version satisfies the given version constraint(s). If it does not (or no version is installed), `davos` will 
install and use a version that does:

```python
# specifically use matplotlib v3.4.2, pip-installing it if needed
smuggle matplotlib.pyplot as plt    # pip: matplotlib==3.4.2

# use a version of seaborn no older than v0.9.1, but prior to v0.11
smuggle seaborn as sns    # pip: seaborn>=0.9.1,<0.11
```

This also works with a specific VCS reference (e.g., git branch, commit, tag, etc.):

```python
# use quail as it existed on GitHub at commit 6c847a4
smuggle quail    # pip: git+https://github.com/ContextLab/quail.git@6c847a4
```

In most cases, smuggling a specific package version or revision is possible even if a different version was previously 
imported. This opens the door to more complex workflows that involve using multiple versions of a package within a 
single interpreter session (e.g., comparing behavior across versions).

`davos` also provides a simple, high-level interface to disable, re-enable, and configure its functionality at any point 
while in use. `davos` currently supports IPython-based notebook environments [@PereGran07] including Jupyter notebooks, 
JupyterLab, and Google Colaboratory. Potential future directions include extending `davos` for use in "vanilla" (i.e., 
non-interactive) Python scripts and adding support for installation via alternative package managers such as `conda`. A 
more extensive guide to using `davos`, additional examples, and a description of how it works are available 
[here](https://github.com/ContextLab/davos).


# Statement of Need

Modern open science practices encourage sharing code and data to enable others to explore, reproduce and extend existing
work. Researchers may seek to share analyses with collaborators while working on a study, with the public upon its 
completion, or with students in classroom or workshop settings. Python is among the most widely used and fastest growing 
scientific programming languages [@MullEtal15]. In addition to the language's high-level, accessible syntax and large 
standard library, the Python ecosystem offers a powerful and extensive data science toolkit designed to facilitate rapid 
development and collaboration, including platforms for interactive development (e.g., Project Jupyter [@KluyEtal16], 
Google Colaboratory), community-driven packages for data manipulation (e.g., NumPy [@HarrEtal20], SciPy [@VirtEtal20], 
Pandas [@McKi10]) and visualization (e.g., Matplotlib [@Hunt07], seaborn [@Wask21]), and myriad other tools. 

However, one challenge posed by the rapidly growing Python ecosystem is that different versions of the same package can 
behave quite differently&mdash;bugs are introduced and fixed, features are implemented and removed, support for Python 
versions is added and dropped, and so on. Thus, Python workflows whose outputs are meant to be stable across different 
environments and over time (e.g., data analyses, tutorials, or demos) are customarily shared alongside a set of fixed 
versions for each package used, often in the form of a configuration file for a development environment (e.g., a 
[Docker](https://www.docker.com/) image, [Singularity](https://sylabs.io/singularity/) image, or 
[conda](https://docs.conda.io/en/latest/) environment) the end user must build and manage themselves. Though powerful, 
such tools are often superfluous for simpler needs. For authors, they require distributing additional files and 
setup instructions alongside code. For users, they require installing additional, more complex software that can be 
cumbersome, resource-intensive, and confusing to navigate without prior familiarity, raising the barrier of entry to 
exploring and reproducing scientific analyses.

One downside of the rapidly growing Python ecosystem is that different versions of the same software package can behave differently
as syntax changes are introduced, bugs are introduced or fixed, features are implemented or removed, support for different versions of
Python is added or dropped, and so on.  This instability can be at odds with the goal of producing reproducible workflows that remain
usable across different development environments and over time.  Through its `smuggle` keyword and onion comments, the `davos` package
improves the stability of Python-based workflows by providing a convenient means of precisely controling and manipulating the environment
in which specific code is executed.

# References
