<div align="center">
  <h1>davos</h1>
  <img src="https://user-images.githubusercontent.com/26118297/116332586-0c6ce080-a7a0-11eb-94ad-0502c96cf8ef.png" width=250/>
  <br>
  <br>
  <a href="https://github.com/ContextLab/davos/actions/workflows/ci-tests-jupyter.yml">
    <img src="https://github.com/ContextLab/davos/actions/workflows/ci-tests-jupyter.yml/badge.svg?branch=main" alt="CI Tests (Jupyter)">
  </a>
  <a href="https://github.com/ContextLab/davos/actions/workflows/ci-tests-colab.yml">
    <img src="https://github.com/ContextLab/davos/actions/workflows/ci-tests-colab.yml/badge.svg?branch=main&event=push" alt="CI Tests (Colab)">
  </a>
  <img src="https://img.shields.io/codefactor/grade/github/paxtonfitzpatrick/davos/main?logo=codefactor&logoColor=brightgreen" alt="code quality (CodeFactor)">
  <img src="https://img.shields.io/badge/mypy-type%20checked-blue" alt="mypy: checked">
  <br>
  <a href="https://pypi.org/project/davos/">
    <img src="https://img.shields.io/pypi/pyversions/davos?logo=python&logoColor=white" alt="Python Versions">
  </a>
  <a href="https://pepy.tech/project/davos">
    <img src="https://static.pepy.tech/personalized-badge/davos?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads" alt="PyPI Downloads">
  </a>
  <br>
  <a href="https://github.com/ContextLab/davos/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/ContextLab/davos" alt="License: MIT">
  </a>
  <br>
  <br>
</div>

> _Someone once told me that the night is dark and full of terrors. And tonight I am no knight. Tonight I am Davos the 
smuggler again. Would that you were an onion._
<div align="right">
  &mdash;<a href="https://gameofthrones.fandom.com/wiki/Davos_Seaworth">Ser Davos Seaworth</a>
  <br>
  <a href="https://en.wikipedia.org/wiki/A_Song_of_Ice_and_Fire"><i>A Clash of Kings</i></a> by
  <a href="https://en.wikipedia.org/wiki/George_R._R._Martin">George R. R. Martin</a>
  <br>
  <br>
</div>


The `davos` library provides Python with an additional keyword: **`smuggle`**. 

[The `smuggle` statement](#the-smuggle-statement) works just like the built-in 
[`import` statement](https://docs.python.org/3/reference/import.html), with one major difference: **you can `smuggle` a 
package without installing it first**.

A key use case for this package is turning standard [IPython notebooks](https://ipython.org/notebook.html) (including [Google Colaboratory notebooks](colab.research.google.com/)) into fully specified Python environments, without the need for external containers or virtualized environments like conda, docker, etc.  This can facilitate sharing, collaboration, and reproducibility.

While the simplest way to use `davos` is as a drop-in replaceemnt for `import`, the way `davos` smuggles packages can be fully controlled and customized using ["_onion comments_"](#the-onion-comment).  Onion comments can be added to lines containing `smuggle` statements to specify which 
**specific package versions** should be installed and imported, and to **fully control how missing packages are installed**.

**To enable the `smuggle` keyword, simply `import davos`**:
```python
import davos

# pip-install numpy v1.20.2, if needed
smuggle numpy as np    # pip: numpy==1.20.2


# the smuggled package is fully imported and usable
arr = np.arange(15).reshape(3, 5)

# and the onion comment guarantees the desired version!
assert np.__version__ == '1.20.2'
```

## Table of contents
- [Installation](#installation)
  - [Latest Stable PyPI Release](#latest-stable-pypi-release)
  - [Latest GitHub Update](#latest-github-update)
- [Overview](#overview)
  - [Smuggling Missing Packages](#smuggling-missing-packages)
  - [Smuggling Specific Package Versions](#smuggling-specific-package-versions)
  - [Use Cases](#use-cases)
    - [Simplify Sharing Reproducible Code & Python Environments](#simplify-sharing-reproducible-code--python-environments)
    - [Guarantee your code always uses the latest version, release, or revision](#guarantee-your-code-always-uses-the-latest-version-release-or-revision)
    - [Compare behavior across package versions](#compare-behavior-across-package-versions)
- [Usage](#usage)
  - [The `smuggle` Statement](#the-smuggle-statement)
    - [Syntax](#smuggle-statement-syntax)
    - [Rules](#smuggle-statement-rules)
  - [The Onion Comment](#the-onion-comment)
    - [Syntax](#onion-comment-syntax)
    - [Rules](#onion-comment-rules)
  - [The `davos` Config](#the-davos-config)
    - [Reference](#config-reference)
    - [Top-level Functions](#top-level-functions)
- [How It Works: The `davos` Parser](#how-it-works-the-davos-parser)
- [Additional Notes](#additional-notes)
  - [Reimplementing installer programs' CLI parsers](#notes-reimplement-cli)
  - [Installer options that affect `davos` behavior](#notes-installer-opts)
  - [Smuggling packages with C-extensions](#notes-c-extensions)
  - [_`from` ... `import` ..._ statements and reloading modules](#notes-from-reload)
  - [Smuggling packages from version control systems](#notes-vcs-smuggle)


## Installation
### Latest Stable PyPI Release
[![](https://img.shields.io/pypi/v/davos?label=PyPI&logo=pypi)](https://pypi.org/project/davos/)
[![](https://img.shields.io/pypi/status/davos)]((https://pypi.org/project/davos/))
[![](https://img.shields.io/pypi/format/davos)]((https://pypi.org/project/davos/))
```sh
pip install davos
```


### Latest GitHub Update
[![](https://img.shields.io/github/commits-since/ContextLab/davos/latest)](https://github.com/ContextLab/davos/releases)
[![](https://img.shields.io/github/last-commit/ContextLab/davos?logo=git&logoColor=white)](https://github.com/ContextLab/davos/commits/main)
[![](https://img.shields.io/github/release-date/ContextLab/davos?label=last%20release)](https://github.com/ContextLab/davos/releases/latest)

```sh
pip install git+https://github.com/ContextLab/davos.git#egg=davos
```


### Installing in Colaboratory
To use `davos` in [Google Colab](https://colab.research.google.com/), add a cell at the top of your notebook with an 
exclamation point (`!`) followed by one of the commands above (e.g., `!pip install davos`). Run the cell to install 
`davos` on the runtime virtual machine. 

**Note**: restarting the Colab runtime does not affect installed packages. However, if the runtime is "factory reset" 
or disconnected due to reaching its idle timeout limit, you'll need to rerun the cell to reinstall `davos` on the fresh 
VM instance.


## Overview
The primary way to use `davos` is via [the `smuggle` statement](#the-smuggle-statement), which is made available 
simply by running `import davos`. Like 
[the built-in `import` statement](https://docs.python.org/3/reference/import.html), the `smuggle` statement is used to 
load packages, modules, and other objects into the current namespace. The main difference between the two is in how 
they handle missing packages and specific package versions.


### Smuggling Missing Packages
`import` requires that packages be installed _before_ the start of the interpreter session. Trying to `import` a package 
that can't be found locally will throw a 
[`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError), and you'll have to 
install the package from the command line, restart the Python interpreter to make the new package importable, and rerun 
your code in full in order to use it.

**The `smuggle` statement, however, can handle missing packages on the fly**. If you `smuggle` a package that isn't 
installed locally, `davos` will install it for you, make its contents available to Python's 
[import machinery](https://docs.python.org/3/reference/import.html), and load it into the namespace for immediate use. 
You can control _how_ `davos` installs missing packages by adding a special type of inline comment called an 
["onion" comment](#the-onion-comment) next to a `smuggle` statement.


### Smuggling Specific Package Versions
One simple but powerful use for [onion comments](#the-onion-comment) is making `smuggle` statements version-sensitive. 

Python does not provide a native, viable way to ensure a third-party package imported at runtime matches a specific 
version or fits a particular [version constraint](https://www.python.org/dev/peps/pep-0440/#version-specifiers). 
Many packages expose their version info via a top-level `__version__` attribute (see 
[PEP 396](https://www.python.org/dev/peps/pep-0396/)), and certain tools (such as the standard library's 
[`importlib.metadata`](https://docs.python.org/3/library/importlib.metadata.html) and 
[`setuptools`](https://setuptools.readthedocs.io/en/latest/index.html)'s 
[`pkg_resources`](https://setuptools.readthedocs.io/en/latest/pkg_resources.html)) attempt to parse version info from 
installed distributions. However, using these to constrain imported package would require writing extra code to compare 
version strings and _still_ having manually installing the desired version and restarting the interpreter any time an 
invalid version is caught.

Additionally, for packages installed through a version control system (e.g., [git](https://git-scm.com/)), this would be 
insensitive to differences between revisions (e.g., commits) within the same semantic version.

**`davos` solves these issues** by allowing you to specify a specific version or set of acceptable versions for each 
smuggled package. To do this, simply provide a 
[version specifier](https://www.python.org/dev/peps/pep-0440/#version-specifiers) in an 
[onion comment](#the-onion-comment) next to the `smuggle` statement:
```python
smuggle numpy as np              # pip: numpy==1.20.2
from pandas smuggle DataFrame    # pip: pandas>=0.23,<1.0
```
In this example, the first line will load [`numpy`](https://numpy.org/) into the local namespace under the alias "`np`", 
just as "`import numpy as np`" would. First, `davos` will check whether `numpy` is installed locally, and if so, whether 
the installed version _exactly_ matches `1.20.2`. If `numpy` is not installed, or the installed version is anything 
other than `1.20.2`, `davos` will use the specified _installer program_, [`pip`](https://pip.pypa.io/en/stable/), to 
install `numpy==1.20.2` before loading the package. 

Similarly, the second line will load the "`DataFrame`" object from the [`pandas`](https://pandas.pydata.org/) library, 
analogously to "`from pandas import DataFrame`". A local `pandas` version of `0.24.1` would be used, but a local version 
of `1.0.2` would cause `davos` to replace it with a valid `pandas` version, as if you had manually run `pip install 
pandas>=0.23,<1.0`. 

In both cases, the imported versions will fit the constraints specified in their [onion comments](#the-onion-comment), 
and the next time `numpy` or `pandas` is smuggled with the same constraints, valid local installations will be found.

You can also force the state of a smuggled packages to match a specific VCS ref (branch, revision, tag, release, etc.). 
For example:
```python
smuggle hypertools as hyp    # pip: git+https://github.com/ContextLab/hypertools.git@98a3d80
```
will load [`hypertools`](https://hypertools.readthedocs.io/en/latest/) (aliased as "`hyp`"), as the package existed 
[on GitHub](https://github.com/ContextLab/hypertools), at commit 
[98a3d80](https://github.com/ContextLab/hypertools/tree/98a3d80). The general format for VCS references in 
[onion comments](#the-onion-comment) follows that of the 
[`pip-install`](https://pip.pypa.io/en/stable/topics/vcs-support) command. See the 
[notes on smuggling from VCS](#notes-vcs-smuggle) below for additional info.

And with [a few exceptions](#notes-c-extensions), smuggling a specific package version will work _even if the package 
has already been imported_!

**Note**: `davos` v0.1 supports [IPython](https://ipython.readthedocs.io/en/stable/) environments  (e.g., 
[Jupyter](https://jupyter.org/) and [Colaboratory](https://colab.research.google.com/) notebooks) only. v0.2 will add 
support for "regular" (i.e., non-interactive) Python scripts.


### Use Cases
#### Simplify sharing reproducible code & Python environments
Different versions of the same package can often behave quite differently&mdash;bugs are introduced and fixed, features 
are implemented and removed, support for Python versions is added and dropped, etc. Because of this, Python code that is 
meant to be _reproducible_ (e.g., tutorials, demos, data analyses) is commonly shared alongside a set of fixed versions 
for each package used. And since there is no Python-native way to specify package versions at runtime (see 
[above](#smuggling-specific-package-versions)), this typically takes the form of a pre-configured development 
environment the end user must build themselves (e.g., a [Docker](https://www.docker.com/) container or 
[conda](https://docs.conda.io/en/latest/) environment), which can be cumbersome, slow to set up, resource-intensive, and 
confusing for newer users, as well as require shipping both additional specification files _and_ setup instructions 
along with your code. And even then, a well-intentioned user may alter the environment in a way that affects your 
carefully curated set of pinned packages (such as installing additional packages that trigger dependency updates).
   
Instead, `davos` allows you to share code with one simple instruction: _just `pip install davos`!_ Replace your `import` 
statements with `smuggle` statements, pin package versions in onion comments, and let `davos` take care of the rest. 
Beyond its simplicity, this approach ensures your predetermined package versions are in place every time your code is 
run.


#### Guarantee your code always uses the latest version, release, or revision
If you want to make sure you're always using the most recent release of a certain package, `davos` makes doing so easy:
```python
smuggle mypkg    # pip: mypkg --upgrade
```
Or if you have an automation designed to test your most recent commit on GitHub:
```python
smuggle mypkg    # pip: git+https://username/reponame.git
```


#### Compare behavior across package versions
The ability to `smuggle` a specific package version even after a different version has been imported makes `davos` a 
useful tool for comparing behavior across multiple versions of the same package, within the same interpreter session:
```python
def test_my_func_unchanged():
    """Regression test for `mypkg.my_func()`"""
    data = list(range(10))
    
    smuggle mypkg                    # pip: mypkg==0.1
    result1 = mypkg.my_func(data)

    smuggle mypkg                    # pip: mypkg==0.2
    result2 = mypkg.my_func(data)

    smuggle mypkg                    # pip: git+https://github.com/MyOrg/mypkg.git
    result3 = mypkg.my_func(data)

    assert result1 == result2 == result3
```


## Usage
### The `smuggle` Statement
#### <a name="smuggle-statement-syntax"></a>Syntax
The `smuggle` statement is meant to be used in place of 
[the built-in `import` statement](https://docs.python.org/3/reference/import.html) and shares
[its full syntactic definition](https://docs.python.org/3/reference/simple_stmts.html#the-import-statement):
```ebnf
smuggle_stmt    ::=  "smuggle" module ["as" identifier] ("," module ["as" identifier])*
                     | "from" relative_module "smuggle" identifier ["as" identifier]
                     ("," identifier ["as" identifier])*
                     | "from" relative_module "smuggle" "(" identifier ["as" identifier]
                     ("," identifier ["as" identifier])* [","] ")"
                     | "from" module "smuggle" "*"
module          ::=  (identifier ".")* identifier
relative_module ::=  "."* module | "."+
```
<sup>
  <i>
    NB: uses the modified BNF grammar notation described in 
    <a href="https://docs.python.org/3/reference">The Python Language Reference</a>, 
    <a href="https://docs.python.org/3/reference/introduction.html#notation">here</a>; see 
    <a href="https://docs.python.org/3/reference/lexical_analysis.html#identifiers">here</a> for the lexical definition 
    of <code>identifier</code>
  </i>
</sup>


In simpler terms, **any valid syntax for `import` is also valid for `smuggle`**.


#### <a name="smuggle-statement-rules"></a>Rules
- Like `import` statements, `smuggle` statements are whitespace-insensitive, unless a lack of whitespace between two 
  tokens would cause them to be interpreted as a different token:
  ```python
  from os.path smuggle dirname, join as opj                       # valid
  from   os   . path   smuggle  dirname    ,join      as   opj    # also valid
  from os.path smuggle dirname, join asopj                        # invalid ("asopj" != "as opj")
  ```
- Any context that would cause an `import` statement _not_ to be executed will have the same effect on a `smuggle` 
  statement:
  ```python
  # smuggle matplotlib.pyplot as plt           # not executed
  print('smuggle matplotlib.pyplot as plt')    # not executed
  foo = """
  smuggle matplotlib.pyplot as plt"""          # not executed
  ```
- Because the `davos` parser is less complex than the full Python parser, there are two, fairly non-disruptive, edge 
  cases where an `import` statement would be syntactically valid but a `smuggle` statement would not:
  1. The [exec](https://docs.python.org/3.8/library/functions.html#exec) function
     ```python
     exec('from pathlib import Path')         # executed
     exec('from pathlib smuggle Path')        # raises SyntaxError
     ```
  2. A one-line [compound statement](https://docs.python.org/3.9/reference/compound_stmts.html#compound-statements) 
     clause:
     ```python
     if True: import random                   # executed
     if True: smuggle random                  # raises SyntaxError
     
     while True: import math; break           # executed
     while True: smuggle math; break          # raises SyntaxError
     
     for _ in range(1): import json           # executed
     for _ in range(1): smuggle json          # raises SyntaxError
     
     # etc...
     ```
- In [IPython](https://ipython.readthedocs.io/en/stable/) environments (e.g., [Jupyter](https://jupyter.org/) & 
  [Colaboratory](https://colab.research.google.com/) notebooks) `smuggle` statements always load names into the global 
  namespace:
  ```python
  # example.ipynb
  import davos
  
  
  def import_example():
      import datetime
  
  
  def smuggle_example():
      smuggle datetime
  
  
  import_example()
  type(datetime)                               # raises NameError
  
  smuggle_example()
  type(datetime)                               # returns
  ```


### The Onion Comment
An _onion comment_ is a special type of inline comment placed on a line containing a `smuggle` statement. Onion comments 
can be used to control how `davos`:
1. determines whether the smuggled package should be installed
2. installs the smuggled package, if necessary

Onion comments are also useful when smuggling a package whose _distribution name_ (i.e., the name 
used when installing it) is different from its _top-level module name_ (i.e., the name used when importing it). Take for 
example:
```python
from sklearn.decomposition smuggle pca    # pip: scikit-learn
```
The onion comment here (`# pip: scikit-learn`) tells `davos` that if "`sklearn`" does not exist 
locally, the "`scikit-learn`" package should be installed.

#### <a name="onion-comment-syntax"></a>Syntax
Onion comments follow a simple but specific syntax, inspired in part by the 
[type comment syntax](https://www.python.org/dev/peps/pep-0484/#type-comments) introduced in 
[PEP 484](https://www.python.org/dev/peps/pep-0484). The following is a loose (pseudo-)syntactic definition for an onion 
comment:
```ebnf
onion_comment   ::=  "#" installer ":" install_opt* pkg_spec install_opt*
installer       ::=  ("pip" | "conda")
pkg_spec        ::=  identifier [version_spec]
```
<sup>
  <i>
    NB: uses the modified BNF grammar notation described in 
    <a href="https://docs.python.org/3/reference">The Python Language Reference</a>, 
    <a href="https://docs.python.org/3/reference/introduction.html#notation">here</a>; see 
    <a href="https://docs.python.org/3/reference/lexical_analysis.html#identifiers">here</a> for the lexical definition 
    of <code>identifier</code>
  </i>
</sup>

where `installer` is the program used to install the package; `install_opt` is any option accepted by the installer's
"`install`" command; and `version_spec` may be a 
[version specifier](https://www.python.org/dev/peps/pep-0440/#version-specifiers) defined by 
[PEP 440](https://www.python.org/dev/peps/pep-0440) followed by a 
[version string](https://www.python.org/dev/peps/pep-0440/#public-version-identifiers), or an alternative syntax valid 
for the given `installer` program. For example, [`pip`](https://pip.pypa.io/en/stable/) uses specific syntaxes for 
[local](https://pip.pypa.io/en/stable/cli/pip_install/#local-project-installs), 
[editable](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs), and 
[VCS-based](https://pip.pypa.io/en/stable/topics/vcs-support) installation.  

Less formally, **an onion comment simply consists of two parts, separated by a colon**: 
1. the name of the installer program (e.g., [`pip`](https://pip.pypa.io/en/stable/))
2. arguments passed to the program's "install" command

Thus, you can essentially think of writing an onion comment as taking the full shell command you would run to install 
the package, and replacing "_install_" with "_:_". For instance, the command:
```sh
pip install -I --no-cache-dir numpy==1.20.2 -vvv --timeout 30
```
is easily translated into an onion comment as:
```python
smuggle numpy    # pip: -I --no-cache-dir numpy==1.20.2 -vvv --timeout 30
```

In practice, onion comments are identified as matches for the
[regular expression](https://en.wikipedia.org/wiki/Regular_expression):
```regex
#+ *(?:pip|conda) *: *[^#\n ].+?(?= +#| *\n| *$)
```
<sup>
  <i>
    NB: support for installing <code>smuggle</code>d packages via 
    <a href="https://docs.conda.io/en/latest/"><code>conda</code></a> will be added in v0.2. For v0.1, 
    "<code>pip</code>" should be used exclusively.
  </i>
</sup>

**Note**: support for installing smuggled packages via the [`conda`](https://docs.conda.io/en/latest/) package manager 
will be added in v0.2. For v0.1, onion comments should always specify "`pip`" as the `installer` program.


#### <a name="onion-comment-rules"></a>Rules
- An onion comment must be placed on the same line as a `smuggle` statement; otherwise, it is not parsed:
  ```python
  # assuming the dateutil package is not installed...
  
  # pip: python-dateutil                       # <-- has no effect
  smuggle dateutil                             # raises InstallerError (no "dateutil" package exists)
  
  smuggle dateutil                             # raises InstallerError (no "dateutil" package exists)
  # pip: python-dateutil                       # <-- has no effect
  
  smuggle dateutil    # pip: python-dateutil   # installs "python-dateutil" package, if necessary
  ```
- An onion comment may be followed by unrelated inline comments as long as they are separated by at least one space:
  ```python
  smuggle tqdm    # pip: tqdm>=4.46,<4.60 # this comment is ignored
  smuggle tqdm    # pip: tqdm>=4.46,<4.60            # so is this one
  smuggle tqdm    # pip: tqdm>=4.46,<4.60# but this comment raises OnionArgumentError
  ```
- An onion comment must be the first inline comment immediately following a `smuggle` statement; otherwise, it is not 
  parsed:
  ```python
  smuggle numpy    # pip: numpy!=1.19.1        # <-- guarantees smuggled version is *not* v1.19.1
  smuggle numpy    # has no effect -->         # pip: numpy==1.19.1 
  ```
  This also allows you to easily "comment out" onion comments:
  ```python
  smuggle numpy    ## pip: numpy!=1.19.1       # <-- has no effect
  ```
- Onion comments are generally whitespace-insensitive, but installer arguments must be separated by at least one space:
  ```python
  from umap smuggle UMAP    # pip: umap-learn --user -v --no-clean     # valid
  from umap smuggle UMAP#pip:umap-learn --user     -v    --no-clean    # also valid
  from umap smuggle UMAP    # pip: umap-learn --user-v--no-clean       # raises OnionArgumentError
  ```
- Onion comments have no effect on standard library modules:
  ```python
  smuggle threading    # pip: threading==9999  # <-- has no effect
  ```
- When smuggling multiple packages with a _single_ `smuggle` statement, an onion comment may be used to refer to the 
  **first** package listed:
  ```python
  smuggle nilearn, nibabel, nltools    # pip: nilearn==0.7.1
  ```
- If multiple _separate_ `smuggle` statements are placed on a single line, an onion comment may be used to refer to the 
  **last** statement:
  ```python
  smuggle gensim; smuggle spacy; smuggle nltk    # pip: nltk~=3.5 --pre
  ```
- For multiline `smuggle` statements, an onion comment may be placed on the first line:
  ```python
  from scipy.interpolate smuggle (    # pip: scipy==1.6.3
      interp1d,
      interpn as interp_ndgrid,
      LinearNDInterpolator,
      NearestNDInterpolator,
  )
  ```
  ... or on the last line:
  ```python
  from scipy.interpolate smuggle (interp1d,                  # this comment has no effect
                                  interpn as interp_ndgrid,
                                  LinearNDInterpolator,
                                  NearestNDInterpolator)     # pip: scipy==1.6.3
  ```
  ... though the first line takes priority:
  ```python
  from scipy.interpolate smuggle (    # pip: scipy==1.6.3    # <-- this version is installed
      interp1d,
      interpn as interp_ndgrid,
      LinearNDInterpolator,
      NearestNDInterpolator,
  )    # pip: scipy==1.6.2                                   # <-- this comment is ignored
  ```
  ... and all comments _not_ on the first or last line are ignored:
  ```python
  from scipy.interpolate smuggle (
      interp1d,                       # pip: scipy==1.6.3    # <-- ignored
      interpn as interp_ndgrid,
      LinearNDInterpolator,           # unrelated comment    # <-- ignored
      NearestNDInterpolator
  )                                   # pip: scipy==1.6.2    # <-- parsed
  ```
- The onion comment is intended to describe how a specific smuggled package should be installed if it is not found 
  locally, in order to make it available for immediate use. Therefore, installer options that either (A) install 
  packages other than the smuggled package and its dependencies (e.g., from a specification file), or (B) cause the 
  smuggled package not to be installed, are disallowed. The options listed below will raise an `OnionArgumentError`:
  - `-h`, `--help`
  - `-r`, `--requirement`
  - `-V`, `--version`


### The `davos` Config
The `davos` config object stores options and data that affect how `davos` behaves. After importing `davos`, the config 
instance (a singleton) for the current session is available as `davos.config`, and its various fields are accessible as 
attributes. The config object exposes a mixture of writable and read-only fields. Most `davos.config` attributes can be 
assigned values to control aspects of `davos` behavior, while others are available for inspection but are set and used 
internally. Additionally, certain config fields may be writable in some situations but not others (e.g. only if the 
importing environment supports a particular feature). Once set, `davos` config options last for the lifetime of the 
interpreter (unless updated); however, they do *not* persist across interpreter sessions. A full list of `davos` config 
fields is available [below](#config-reference):

#### <a name="config-reference"></a>Reference
| Field | Description | Type | Default | Writable? |
| :---: | --- | :---: | :---: | :---: |
| `active` | Whether or not the `davos` parser should be run on subsequent input (cells, in Jupyter/Colab notebooks). Setting to `True` activates the `davos` parser, enables the `smuggle` keyword, and injects the `smuggle()` function into the user namespace. Setting to `False` deactivates the `davos` parser, disables the `smuggle` keyword, and removes "`smuggle`" from the user namespace (if it holds a reference to the `smuggle()` function). See [How it Works](#how-it-works) for more info. | `bool` | `True` | ✅ |
| `auto_rerun` | If `True`, when smuggling a previously-imported package that cannot be reloaded (see [Smuggling packages with C-extensions](#notes-c-extensions)), `davos` will automatically restart the interpreter and rerun all code up to (and including) the current `smuggle` statement. Otherwise, issues a warning and prompts the user with buttons to either restart/rerun or continue running. | `bool` | `False` | ✅ (**Jupyter notebooks only**) |
| `confirm_install` | Whether or not `davos` should require user confirmation (`[y/n]` input) before installing a smuggled package | `bool` | `False` | ✅ |
| `environment` | A label describing the environment into which `davos` was running. Checked internally to determine which interchangeable implementation functions are used, whether certain config fields are writable, and various other behaviors | `Literal['Python', 'IPython<7.0', 'IPython>=7.0', 'Colaboratory']` | N/A | ❌ |
| `ipython_shell` | The global IPython interactive shell instance | [`IPython.core`<br>`.interactiveshell`<br>`.InteractiveShell`](https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.interactiveshell.html#IPython.core.interactiveshell.InteractiveShell) | N/A | ❌ |
| `noninteractive` | Set to `True` to run `davos` in non-interactive mode (all user input and confirmation will be disabled). **NB**:<br>1. Setting to `True` disables `confirm_install` if previously enabled <br>2. If `auto_rerun` is `False` in non-interactive mode, `davos` will throw an error if a smuggled package cannot be reloaded | `bool` | `False` | ✅ (**Jupyter notebooks only**) |
| `pip_executable` | The path to the `pip` executable used to install smuggled packages. Must be a path (`str` or [`pathlib.Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) to a real file. Default is programmatically determined from Python environment; falls back to `sys.executable -m pip` if executable can't be found | `str` | `pip` exe path or `sys.executable -m pip` | ✅ |
| `smuggled` | A cache of packages smuggled during the current interpreter session. Formatted as a `dict` whose keys are package names and values are the (`.split()` and `';'.join()`ed) onion comments. Implemented this way so that any non-whitespace change to installer arguments  re-installation | `dict[str, str]` | `{}` | ❌ |
| `suppress_stdout` | If `True`, suppress all unnecessary output issued by both `davos` and the installer program. Useful when smuggling packages that need to install many dependencies and therefore generate extensive output. If the installer program throws an error while output is suppressed, both stdout & stderr will be shown with the traceback | `bool` | `False` | ✅ |

#### <a name="top-level-functions"></a>Top-level Functions
`davos` also provides a few convenience for reading/setting config values:
- **`davos.activate()`**
  Activate the `davos` parser, enable the `smuggle` keyword, and inject the `smuggle()` function into the namespace. 
  Equivalent to setting `davos.config.active = True`. See [How it Works](#how-it-works) for more info.

- **`davos.deactivate()`**
  Deactivate the `davos` parser, disable the `smuggle` keyword, and remove the name `smuggle` from the namespace if (and 
  only if) it refers to the `smuggle()` function. If `smuggle` has been overwritten with a different value, the variable 
  will not be deleted. Equivalent to setting `davos.config.active = False`. See [How it Works](#how-it-works) for more 
- info.

- **`davos.is_active()`**
  Return the current value of `davos.config.active`.

- **`davos.configure(**kwargs)`**
  Set multiple `davos.config` fields at once by passing values as keyword arguments, e.g.:
  ```python
  import davos
  davos.configure(active=False, noninteractive=True, pip_executable='/usr/bin/pip3')
  ```
  is equivalent to:
  ```python
  import davos
  davos.active = False
  davos.noninteractive = True
  davos.pip_executable = '/usr/bin/pip3'
  ```

## How It Works: The `davos` Parser
Functionally, importing `davos` appears to enable a new Python keyword, "_`smuggle`_". However, `davos` doesn't actually 
modify the rules or [reserved keywords](https://docs.python.org/3/reference/lexical_analysis.html#keywords) used by 
Python's parser and lexical analyzer in order to do so&mdash;in fact, modifying the Python grammar is not possible at 
runtime and would require rebuilding the interpreter. Instead, in [IPython](https://ipython.readthedocs.io/en/stable/) 
enivonments like [Jupyter](https://jupyter.org/) and 
[Colaboratory](https://colab.research.google.com/notebooks/intro.ipynb) notebooks, `davos` implements the `smuggle` 
keyword via a combination of namespace injections and its own (far simpler) custom parser.

The `smuggle` keyword can be enabled and disabled at will by "activating" and "deactivating" `davos` (see the 
[`davos` Config Reference](config-reference) and [Top-level Functions](#top-level-functions), above). When `davos` is 
imported, it is automatically activated by default. Activating `davos` triggers two things:
1. The _`smuggle()` function_ is injected into the `IPython` user namespace
2. The _`davos` parser_ is registered as a
[custom input transformer](https://ipython.readthedocs.io/en/stable/config/inputtransforms.html)

IPython preprocesses all executed code as plain text before it is sent to the Python parser in order to handle 
special constructs like [`%magic`](https://ipython.readthedocs.io/en/stable/interactive/magics.html) and 
[`!shell`](https://ipython.readthedocs.io/en/stable/interactive/reference.html#system-shell-access) commands. `davos`
hooks into this process to transform `smuggle` statements into syntactically valid Python code. The `davos` 
parser uses [this regular expression](https://github.com/ContextLab/davos/blob/main/davos/core/regexps.py) to match each
line of code containing a `smuggle` statement (and, optionally, an onion comment), extracts information from its text, 
and replaces it with an analogous call to the _`smuggle()` function_. Thus, even though the code visible to the user may 
contain `smuggle` statements, e.g.:
```python
smuggle numpy as np    # pip: numpy>1.16,<=1.20 -vv
```
the code that is actually executed by the Python interpreter will not:
```python
smuggle(name="numpy", as_="np", installer="pip", args_str="""numpy>1.16,<=1.20 -vv""", installer_kwargs={'editable': False, 'spec': 'numpy>1.16,<=1.20', 'verbosity': 2})
```

The `davos` parser can be deactivated at any time, and doing so triggers the opposite actions of activating it:
1. The name "`smuggle`" is deleted from the `IPython` user namespace, *unless it has been overwritten and no longer 
   refers to the `smuggle()` function*
2. The `davos` parser input transformer is deregistered.

**Note**: in Jupyter and Colaboratory notebooks, IPython parses and transforms all text in a cell before sending it 
to the kernel for execution. This means that importing or activating `davos` will not make the `smuggle` statement 
available until the _next_ cell, because all lines in the current cell were transformed before the `davos` parser was 
registered. However, _deactivating_ `davos` disables the `smuggle` statement immediately&mdash;although the `davos` 
parser will have already replaced all `smuggle` statements with `smuggle()` function calls, removing the function from 
the namespace causes them to throw `NameError`.


## Additional Notes
- <a name="notes-reimplement-cli"></a>**Reimplementing installer programs' CLI parsers**

  The `davos` parser extracts info from onion comments by passing them to a (slightly modified) reimplementation of 
  their specified installer program's CLI parser. This is somewhat redundant, since the arguments will eventually be 
  re-parsed by the _actual_ installer program if the package needs to be installed. However, it affords a number of 
  advantages, such as: 
  - detecting errors early during the parser phase, before spending any time running code above the line containing the 
    `smuggle` statement
  - preventing shell injections in onion comments&mdash;e.g., `#pip: --upgrade numpy && rm -rf /` fails due to the 
    `OnionParser`, but would otherwise execute successfully.
  - allowing certain installer arguments to temporarily influence `davos` behavior while smuggling the current package 
    (see [Installer options that affect `davos` behavior](#notes-installer-opts) below for specific info)

- <a name="notes-installer-opts"></a>**Installer options that affect `davos` behavior**
  
  Passing certain options to the installer program via an [onion comment](#the-onion-comment) will also affect the 
  corresponding `smuggle` statement in a predictable way:

  - [**`--force-reinstall`**](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-force-reinstall) | 
    [**`-I`, `--ignore-installed`**](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-I) | 
    [**`-U`, `--upgrade`**](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-I)
      
    The package will be installed, even if it exists locally

  - [**`--no-input`**](https://pip.pypa.io/en/stable/cli/pip/#cmdoption-no-input)
      
    Disables input prompts, analogous to temporarily setting `davos.config.noninteractive` to `True`. Overrides value 
    of `davos.config.confirm_install`.

  - [**`--src <dir>`**](https://pip.pypa.io/en/stable/cli/pip/#cmdoption-no-input) | 
    [**`-t`, `--target <dir>`**](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-t)
      
    Prepends `<dir>` to [`sys.path`](https://docs.python.org/3/library/sys.html#sys.path) if not already present so 
    the package can be imported.
    
- <a name="notes-c-extensions"></a>**Smuggling packages with C-extensions**

  Some Python packages that rely heavily on custom data types implemented via 
  [C-extensions](https://docs.python.org/3.9/extending/extending.html) (e.g., `numpy`, `pandas`) dynamically generate 
  modules defining various C functions and data structures, and link them to the Python interpreter when they are first 
  imported. Depending on how these objects are initialized, they may not be subject to normal garbage collection, and 
  persist despite their reference count dropping to zero. This can lead to unexpected errors when reloading the Python 
  module that creates them, particularly if their dynamically generated source code has been changed (e.g., because the 
  reloaded package is a newer version).
  
  This can occasionally affect `davos`'s ability to `smuggle` a new version of a package (or dependency) that was 
  previously imported. To handle this, `davos` first checks each package it installs against 
  [`sys.modules`](https://docs.python.org/3.9/library/sys.html#sys.modules). If a different version has already been 
  loaded by the interpreter, `davos` will attempt to replace it with the requested version. If this fails, `davos` will 
  restore the old package version _in memory_, while replacing it with the new package version _on disk_. This allows 
  subsequent code that uses the non-reloadable module to still execute in most cases, while dependency checks for other 
  packages run against the updated version. Then, depending on the value of `davos.config.auto_rerun`, `davos` will 
  either either automatically restart the interpreter to load the updated package, prompt you to do so, or raise an 
  exception.

- <a name="notes-from-reload"></a>**_`from` ... `import` ..._ statements and reloading modules**

  The Python docs for [`importlib.reload()`](https://docs.python.org/3/library/importlib.html#importlib.reload) include 
  the following caveat:
  > If a module imports objects from another module using 
  > [`from`](https://docs.python.org/3/reference/simple_stmts.html#from) … 
  > [`import`](https://docs.python.org/3/reference/simple_stmts.html#import) …, calling 
  > [`reload()`](https://docs.python.org/3/library/importlib.html#importlib.reload) for the other module does 
  > not redefine the objects imported from it — one way around this is to re-execute the `from` statement, another is to 
  > use `import` and qualified names (_module.name_) instead.

  The same applies to smuggling packages or modules from which objects have already been loaded. If object _`name`_ from 
  module _`module`_ was loaded using either _`from module import name`_ or _`from module smuggle name`_, subsequently 
  running _`smuggle module    # pip --upgrade`_ will in fact install and load an upgraded version of _`module`_, but the 
  the _`name`_ object will still be that of the old version! To fix this, you can simply run _`from module smuggle 
  name`_ either instead in lieu of or after _`smuggle module`_.
  

- <a name="notes-vcs-smuggle"></a>**Smuggling packages from version control systems**

  The first time during an interpreter session that a given package is installed from a VCS URL, it is assumed not to be 
  present locally, and is therefore freshly installed. `pip` clones non-editable VCS repositories into a temporary 
  directory, runs `setup.py install`, and then immediately deletes them. Since no information is retained about the 
  state of the repository at installation, it is impossible to determine whether an existing package satisfies the state 
  (i.e., branch, tag, commit hash, etc.) requested for smuggled package.

[comment]: <> (- As with _all_ code, you should use caution when running Python code containing `smuggle` statements that was not written by you or someone you know. )
