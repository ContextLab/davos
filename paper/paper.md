---
title: 'Davos: The Python package smuggler'
tags:
 - Python
 - Jupyter Notebook
 - JupyterLab
 - Google Colab
 - package-management
 - import
 - install
 - pip
authors:
 - name: Paxton C. Fitzpatrick^[corresponding author]
   orcid: 0000-0003-0205-3088
   affiliation: 1
 - name: Jeremy R. Manning
   orcid: 0000-0001-7613-4732
   affiliation: 1
affiliations:
 - name: Department of Psychological and Brain Sciences, Dartmouth College
   index: 1
date: 14 November 2021
bibliography: paper.bib
---

# Summary and overview

The `davos` library provides Python with a single keyword-like object,
`smuggle`, which is like a quick (and often dirty) wrapper for `import`.
Whereas you cannot `import` a library that hasn't been installed yet, you can
easily `smuggle` a not-yet-installed library:

```python
import davos              # this adds the smuggle "keyword" to the Python workspace
smuggle seaborn as sns    # installs seaborn if needed!

# now you can use seaborn as if you had imported it the "normal" way
titanic = sns.utils.load_dataset('titanic')
sns.barplot(data=titanic, x='class', y='survived', hue='sex', palette=sns.light_palette('seagreen'))
```

As of its initial release, `davos` may only be used in [Google
Colaboratory](https://colab.research.google.com/) or
[Jupyter](https://jupyter.org/) notebooks (i.e., `.ipynb` files).  Use in Python
scripts (`.py` files) is not supported.

A convenient way to use `davos` is as a means of sharing a complete analysis
environment (dependencies, data, and code) in a single notebook file.

Including the lines

```python
!pip install davos
import davos
```
at the start of a notebook will install and import the `davos` library.

If subsequent uses of `import` are replaced with `smuggle`, `davos` will install
the to-be-imported library or package if needed, and then import it into the
current workspace.

## Using the `smuggle` keyword-like object

Once you import the `davos` library, you can use `smuggle` as a stand in keyword-like object anywhere you would have otherwise used `import`.  Any of the following will work:

```python
smuggle pickle                             # built-in modules
from matplotlib smuggle pyplot as plt      # "from" keyword, renaming sub-modules using "as"
from scipy.spatial.distance smuggle cdist  # import sub-modules using dot notation
smuggle os, sys                            # comma notation
smuggle pandas as pd, numpy as np          # comma notation with renaming using "as"
```

The `davos` library also supports passing customizable version numbers or
installation instructions to `pip` or `conda`, using a syntax called "onion
comments."  These may be used as follows:

```python
#install packages whose pip name and import name do not match
smuggle umap                   # pip: umap-learn

#specify a package's version number
smuggle numpy as np            # pip: numpy==1.20.2
from pandas smuggle DataFrame  # pip: pandas>=0.23,<1.0

#install a package directly from a version control system (e.g., GitHub)
smuggle hypertools as hyp      # pip: git+https://github.com/ContextLab/hypertools.git@36c12fd
```

The general syntax for onion comments is:

```ebnf
onion_comment   ::=  "#" installer ":" install_opt* pkg_spec install_opt*
installer       ::=  ("pip" | "conda")
pkg_spec        ::=  identifier [version_spec]
```

## Tricky bits

If you have previously imported (or smuggled) a library into your workspace,
onion comments may often be used to *change* the version number of the given
library.  For example:

```python
smuggle seaborn as sns # pip: seaborn==0.11.1
sns.__version__        #version is '0.11.1'

smuggle seaborn as sns # pip: seaborn==0.9.0
sns.__version__        #version is now '0.9.0`
```

This can serve as a hack for leveraging functionality that is
only available in specific versions of a given library.

In general, packages that are installed using `smuggle` are immediately available
within the current workspace, in the current runtime environment.  Some exceptions to
this behavior include:
  - Libraries like `numpy`, which wrap `C` functions, cannot be updated within
  the current runtime. The runtime must be manually restarted in order to complete
  the installation of these libraries.
  - Davos cannot be used to smuggle himself; `smuggle davos` will raise an exception.
  - The `smuggle` keyword may not be used inside of `exec` or `eval` statements.  To
  use the `smuggle` functionality within these statements, we also provide `smuggle` as a
  standard Python function; this function is available as `davos.smuggle`.
  - Davos does not resolve package conflicts that may result from updating already-installed
  packages.  For example, if `library1` depends on `library2==1.0.1`, then smuggling 
  a *different* version of `library2` will break `library1`'s installation.  Because
  `davos` wraps `pip` and `conda`, any package conflicts that are not resolved by
  `pip` or `conda` will not be resolved by `davos` either.

# Installation

You can install the latest official version of `davos` with `pip` as follows:

```bash
pip install --upgrade davos
```

To install the cutting (bleeding) edge version directly from git, use:

```bash
pip install git+https://github.com/ContextLab/davos.git#egg=davos
```

# Origin of the name

The package name is inspired by [Davos Seaworth](https://gameofthrones.fandom.com/wiki/Davos_Seaworth), a famous smuggler from the [Song of Fire and Ice](https://en.wikipedia.org/wiki/A_Song_of_Ice_and_Fire) series by [George R. R. Martin](https://en.wikipedia.org/wiki/George_R._R._Martin).

# More information

Additional documentation, including more advanced usage instructions,
implementation details, and other details may be found in the package's
[README](https://github.com/ContextLab/davos/blob/main/README.md) file.
