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

Additionally, certain arguments can be added to skip searching the local environment altogether, and instead always 
install a fresh version of the package:

```python
# install hypertools v0.7 without first checking for it locally
smuggle hypertools as hyp    # pip: hypertools==0.7 --ignore-installed

# always install the latest version of requests, including pre-release and development versions
from requests smuggle Session    # pip: requests --upgrade --pre
```

Because `davos` parses onion comments at runtime and manages required packages in a just-in-time manner, it is possible 
in most cases to `smuggle` a specific package version (or revision) even when a different version has already been 
loaded. This opens the door to more complex use cases involving using multiple versions of a package within a single 
interpreter session (e.g., using an unstable development version that supports a new feature only when necessary, or 
comparing behavior across versions for regression testing).

`davos` provides a simple, high-level interface that allows the user to disable, re-enable, and configure its 
functionality at any point throughout their code. `davos` currently supports IPython-based notebook environments 
[@PereGran07] including Jupyter notebooks, JupyterLab, and Google Colaboratory. Potential future directions include 
extending `davos` for use in "vanilla" (i.e., non-interactive) Python scripts and adding support for installation via 
alternative package managers such as `conda`. `davos` is currently being used in a number of ongoing projects, as well 
as online demos for [*Storytelling with Data*](https://github.com/ContextLab/storytelling-with-data) (@Mann21b; an open 
course on data science, visualization, and communication) and `abstract2paper` (@Mann21a; an toy application of 
[GPT-Neo](https://github.com/EleutherAI/gpt-neo)). A more extensive guide to using `davos`, additional examples, and a 
description of how it works are available [here](https://github.com/ContextLab/davos).


# Statement of Need

Modern open science practices encourage sharing code and data to enable others to explore, reproduce and extend existing
work. Researchers may seek to share analyses with collaborators while working on a study, with the public upon its 
completion, or with students in classroom or workshop settings. Python is among the most widely used and fastest-growing 
scientific programming languages [@MullEtal15]. In addition to the language's high-level, accessible syntax and large 
standard library, the Python ecosystem offers a powerful and extensive data science toolkit designed to facilitate rapid 
development and collaboration, including platforms for interactive development (e.g., Project Jupyter [@KluyEtal16], 
Google Colaboratory), community-maintained libraries for data manipulation (e.g., NumPy [@HarrEtal20], SciPy 
[@VirtEtal20], Pandas [@McKi10]) and visualization (e.g., Matplotlib [@Hunt07], seaborn [@Wask21]), and myriad other 
tools. 

However, one challenge posed by the rapidly growing Python ecosystem is that different versions of the same package can 
behave quite differently&mdash;bugs are introduced and fixed, features are implemented and removed, support for Python 
versions is added and dropped, and so on. Thus, Python workflows whose outputs must be consistent over time and across 
users (e.g., data analyses, tutorials, or demos) are customarily shared alongside a set of fixed versions for each 
package used. This often takes the form of a configuration file for a development environment (e.g., a 
[Docker](https://www.docker.com/) image, [Singularity](https://sylabs.io/singularity/) image, or 
[conda](https://docs.conda.io/en/latest/) environment) the end user must build and manage themselves. While powerful,
such tools are often superfluous for simpler needs and add an additional level of complexity that can raise the 
barriers to entry for sharing, exploring, and contributing to research-related code. For authors, they require 
distributing additional files and setup instructions alongside the code itself. For users, they require installing and 
using additional software that can be cumbersome, resource-intensive, and confusing to navigate without prior 
familiarity.

Instead, `davos` offers a mechanism for defining a set of required Python packages directly within the code that uses 
them. The first improvement this framework affords is the ability to create reproducible workflows that can be shared 
and run without the need for extra configuration files, software, and setup in order to do so. This can expedite 
collaboration between reserachers and improve accessibility for less experienced users. `davos` is intended for sharing 
relatively simple, Python-specific requirements, whereas, for example, if an analysis or demo notebook relies heavily on
non-Python software, Docker (possibly in combination with `davos`) is likely a better option. Additionally, while 
`davos` itself is not designed as a tool for isolating Python environments, this can easily be achieved by running 
`davos`-based notebooks via Colaboratory or inside an empty virtual environment quickly created using Python's built-in 
[`venv`](https://docs.python.org/3/library/venv.html) module.

The second advantage to using `davos` is that it helps ensure dependencies *remain* present and stable over time. Most 
requirement specification schemes entail building a development environment in which a particular set of packages and 
versions are initially installed, but not constrained past that point. This can pose unexpected challenges for 
researchers working on data analyses within such a preconfigured environment, as well as those with whom their code and 
environment may eventually be shared: it can be easy to inadvertently alter the development environment after its inital 
setup. For example, deciding to perform aditional analyses can mean installing additional packges at a later point. This 
can trigger updates to packages used in earlier analyses that can easily go unnoticed and potentially affect their 
behavior. `davos` provides a safeguard against this by continuing to enforce pinned package versions each time `smuggle`
statements are run, ensuring that any accidental changes to the environment will be caught, and will not affect 
reproducibility.


# Origin of the Name

The package name is inspired by [Davos Seaworth](https://en.wikipedia.org/wiki/Davos_Seaworth), a smuggler often 
referred to as "the Onion Knight" from the series 
[A song of Ice and Fire](https://en.wikipedia.org/wiki/A_Song_of_Ice_and_Fire) by 
[George R. R. Martin](https://en.wikipedia.org/wiki/George_R._R._Martin).


# References
