<div align="center">
  <h1>davos</h1>
  <img src="https://user-images.githubusercontent.com/26118297/116332586-0c6ce080-a7a0-11eb-94ad-0502c96cf8ef.png" width=250/>
</div>

🟥🟥🟥 add badges 🟥🟥🟥

[![CI Tests (Jupyter)](https://github.com/ContextLab/davos/actions/workflows/ci-tests-jupyter.yml/badge.svg?branch=main)](https://github.com/ContextLab/davos/actions/workflows/ci-tests-jupyter.yml)
[![CI Tests (Colab)](https://github.com/ContextLab/davos/actions/workflows/ci-tests-colab.yml/badge.svg?branch=main&event=push)](https://github.com/ContextLab/davos/actions/workflows/ci-tests-colab.yml)

[![](https://img.shields.io/pypi/v/davos?color=blue)](https://pypi.org/project/davos/)
[![](https://img.shields.io/pypi/pyversions/davos)](https://pypi.org/project/davos/)
[![](https://img.shields.io/github/license/ContextLab/davos)](https://github.com/ContextLab/davos/blob/main/LICENSE)

> _Someone once told me that the night is dark and full of terrors. And tonight I am no knight. Tonight I am Davos the 
smuggler again. Would that you were an onion._
<div align="right">
    &mdash;<a href="https://gameofthrones.fandom.com/wiki/Davos_Seaworth">Ser Davos Seaworth</a>
    <br>
    <a href="https://en.wikipedia.org/wiki/A_Song_of_Ice_and_Fire"><i>A Clash of Kings</i></a> by
    <a href="https://en.wikipedia.org/wiki/George_R._R._Martin">George R. R. Martin</a>
</div>


The `davos` library provides Python with an additional keyword: **`smuggle`**. 

[`smuggle` statements](#the-smuggle-statement) work just like standard 
[`import` statements](https://docs.python.org/3/reference/import.html) with one major addition: _you can `smuggle` a 
package without installing it first_. A special type of comment (called an ["**onion**"](#the-onion-comment)) can also 
be added after a `smuggle` statement, allowing you to _`smuggle` specific package versions_ and fully control 
installation of missing packages.

To enable the `smuggle` keyword, simply `import davos`:
```python
import davos

# pip-install numpy if needed
smuggle numpy as np    # pip: numpy==1.20.2

# the smuggled package is fully imported and usable
arr = np.arange(15).reshape(3, 5)
# and the onion comment guarantees the desired version!
assert np.__version__ == '1.20.2'
```

## Table of contents
- [Installation](#installation)
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
- [Examples](#examples)
- [How it works](#how-it-works)
- [Additional Notes](#additional-notes)
  - [Installer options that affect `davos` behavior](#notes-installer-opts)
  - [Smuggling packages with C-extensions](#notes-c-extensions)
  - [Smuggling packages from version control systems](#notes-vcs-smuggle)


## Installation
### Latest stable PyPI release
🟥🟥🟥 add badges 🟥🟥🟥
```sh
pip install davos
```


### Latest unstable GitHub update
🟥🟥🟥 add badges 🟥🟥🟥
```sh
pip install git+https://github.com/ContextLab/davos.git#egg=davos
```


### Installing in Colaboratory
To use `davos` in [Google Colab](https://colab.research.google.com/), add a cell at the top of your notebook with an 
exclamation point (`!`) followed by one of the install commands above (e.g., `!pip install davos`). Run the cell to 
install `davos` on the runtime virtual machine. 

Note that restarting the notebook runtime does not affect installed packages. However, if the runtime is "factory reset" 
or disconnected due to reaching its idle timeout limit, you'll need to rerun the cell to reinstall `davos` on the fresh 
VM instance.


## Overview
The primary way to use `davos` is via [the `smuggle` statement](#the-smuggle-statement), which is made available 
throughout your code simply by running `import davos`. Like 
[the built-in `import` statement](https://docs.python.org/3/reference/import.html), the `smuggle` statement is used to 
load code from another package or module into the current namespace. The main difference between the two is in how they 
handle missing packages and package versions.


### Smuggling Missing Packages
`import` requires that packages be installed _before_ the start of the interpreter session. If you try to `import` a 
package that can't be found locally, Python will raise a 
[`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError), and you will have to 
install the package, restart the interpreter to make the new package available, and rerun your code in full.

`smuggle`, however, can handle missing packages on the fly. If you `smuggle` a package that isn't installed locally, 
`davos` will install it, immediately make its contents accessible to the interpreter's
[import machinery](https://docs.python.org/3/reference/import.html), and load the package into the local namespace for 
use. You can add an inline ["onion" comment](#the-onion-comment) after a `smuggle` statement to customize how 
`davos` will install the package, if it can't be found locally.

An [onion comment](#the-onion-comment) is also useful for smuggling a package whose _distribution name_ (i.e., the name 
used when installing it) is different from its _top-level module name_ (i.e., the name used when importing it). For 
example:
```python
from sklearn.decomposition smuggle pca    # pip: scikit-learn
```
The [onion comment](#the-onion-comment) here (`# pip: scikit-learn`) tells `davos` that if "`sklearn`" does not exist 
locally, the "`scikit-learn`" package should be installed.


### Smuggling Specific Package Versions
[Onion comments](#the-onion-comment) can also be used to make `smuggle` statements version-sensitive. 

Python does not provide a way to programmatically ensure a package imported at runtime matches a specific version, or 
fits a particular [version constraint](https://www.python.org/dev/peps/pep-0440/#version-specifiers). Although many 
packages expose their version info via a `__version__` attribute (see 
[PEP 396](https://www.python.org/dev/peps/pep-0396/)), using this to enforce package versions is generally not viable, 
as doing so would require:

- writing a potentially large amount of additional code to compare package versions
- replacing all `from foo import bar` statements with `import foo` to make `foo.__version__` accessible
- manually installing the desired version, restarting the interpreter, and rerunning your code in full every time an 
  invalid version is found
- devising an entirely separate approach for packages that don't have a `__version__` attribute in the first place!

Additionally, for packages installed through a version control system (e.g., git), this would be insensitive to 
differences between revisions (e.g., commits) within the same semantic version.

**`davos` solves these issues** by allowing you to constrain each package you `smuggle` to a specific version or range 
of acceptable versions. This can be done simply by placing a 
[version specifier](https://www.python.org/dev/peps/pep-0440/#version-specifiers) in an 
[onion comment](#the-onion-comment) next to the corresponding `smuggle` statement:
```python
smuggle numpy as np              # pip: numpy==1.20.2
from pandas smuggle DataFrame    # pip: pandas>=0.23,<1.0
```
In this example, the first line will load [`numpy`](https://numpy.org/) into the local namespace under the alias "`np`", 
just as "`import numpy as np`" would. `davos` will first check whether `numpy` is installed locally, and if so, whether 
the installed version _exactly_ matches `1.20.2`. If `numpy` is not installed, or the installed version is anything 
other than `1.20.2`, `davos` will use the specified _installer_, `pip`, to install `numpy==1.20.2` before loading the 
package. 

Similarly, the second line will load the "`DataFrame`" object from the [`pandas`](https://pandas.pydata.org/) library, 
analogously to "`from pandas import DataFrame`". A local `pandas` version of `0.24.1` would be used, but a local version 
of `1.0.2` would cause `davos` to install a valid `pandas` version as if you had manually run `pip install 
pandas>=0.23,<1.0`. 

In both cases, the imported versions will fit the constraints specified in their [onion comments](#the-onion-comment), 
and the next time `numpy` or `pandas` is smuggled with the same constraints, valid local installations will be found.

You can also force the state of a packages to match a specific VCS branch, revision, ref, or release. For example:
```python
smuggle hypertools as hyp    # pip: git+https://github.com/ContextLab/hypertools.git@36c12fd
```
will load [`hypertools`](https://hypertools.readthedocs.io/en/latest/) (aliased as "`hyp`"), as the package existed 
[on GitHub](https://github.com/ContextLab/hypertools), at commit 
[36c12fd](https://github.com/ContextLab/hypertools/tree/36c12fd). The general format for VCS references in 
[onion comments](#the-onion-comment) follows that of the 
[`pip-install`](https://pip.pypa.io/en/stable/cli/pip_install/#vcs-support) command. See the 
[notes on smuggling from VCS](#notes-vcs-smuggle) below for additional info.

With [a few exceptions](#notes-c-extensions), smuggling a specific package version will work _even if the package 
has already been imported_.


### Use Cases
#### Simplify sharing reproducible code & Python environments
Different versions of the same package can often behave quite differently&mdash;bugs are introduced and fixed, features 
are implemented and removed, support for Python versions is added and dropped, etc. Because of this, Python code that is 
meant to be _reproducible_ (e.g., tutorials, demos, data analyses) is commonly shared alongside a set of a set of fixed 
versions for each package used. And since there is no Python-native way to specify package versions at runtime (see 
[above](#smuggling-specific-package-versions)), this often takes the form of a pre-configured development environment 
(e.g., a [Docker](https://www.docker.com/) container), which can be cumbersome, slow to set up, resource-intensive, and 
confusing for newer users, as well as require shipping both additional specification files _and_ instructions along with 
your code. Even then, a well-intentioned user may alter the environment in a way that affects your carefully curated set 
of pinned package versions (such as installing additional packages that trigger dependency updates).
   
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
useful tool for comparing behavior across multiple versions of the same package, all within the same interpreter 
session:
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
The `smuggle` statement is designed to be used in place of 
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


In simpler terms, **any valid syntax for `import` is also a valid syntax for `smuggle`** (`smuggle foo`, `from foo.bar 
smuggle baz as qux`, etc.). See [below](#valid-syntaxes) for a full list of valid forms.


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
- determines whether the `smuggle`d package should be installed
- installs the `smuggle`d package, if necessary


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
for the given `installer` program. For example, `pip` uses specific syntax for 
[local](https://pip.pypa.io/en/stable/cli/pip_install/#local-project-installs), 
[editable](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs), and 
[VCS-based](https://pip.pypa.io/en/stable/cli/pip_install/#vcs-support) installation.  **Note**: support for installing 
`smuggle`d packages via the [`conda`](https://docs.conda.io/en/latest/) package manager will be added in v0.2. For v0.1, 
"`pip`" should always be passed as the `installer` program.

Less formally, an onion comment simply consists of two parts, separated by a colon: 
1. the name of the installer program (e.g., *`pip`*)
2. the arguments passed to the program's "install" command

Thus, you can essentially think of writing an onion comment as taking the full shell command you would run to install 
the package, and replacing "_install_" with "_:_". For instance, the command:
```sh
pip install -I --no-cache-dir numpy==1.20.2 -vvv
```
is easily translated into an onion comment as:
```python
smuggle numpy    # pip: -I --no-cache-dir numpy==1.20.2 -vvv
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
- If multiple _separate_ `smuggle` statements appear on a single line separated by semicolons, an onion comment 
  may be used to modify the **last** `smuggle` statement:
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
  or on the last line:
  ```python
  from scipy.interpolate smuggle (interp1d,                  # this comment has no effect
                                  interpn as interp_ndgrid,
                                  LinearNDInterpolator,
                                  NearestNDInterpolator)     # pip: scipy==1.6.3
  ```
  though the first line takes priority:
  ```python
  from scipy.interpolate smuggle (    # pip: scipy==1.6.3    # <-- this version is installed
      interp1d,
      interpn as interp_ndgrid,
      LinearNDInterpolator,
      NearestNDInterpolator,
  )    # pip: scipy==1.6.2                                   # <-- this comment is ignored
  ```
  and all comments _not_ on the first or last line are ignored:
  ```python
  from scipy.interpolate smuggle (
      interp1d,    # pip: scipy==1.6.3                       # <-- ignored
      interpn as interp_ndgrid,
      LinearNDInterpolator,    # unrelated comment           # <-- ignored
      NearestNDInterpolator
  )    # pip: scipy==1.6.2                                   # <-- parsed
  ```
- Because the onion comment is meant to control installation of a single `smuggle`d package, and because the purpose of 
  installing that package is to make it available for immediate use, installer options that either A) install more than 
  a single package and its dependencies (e.g., from a specification file), or B) do not install the specified package 
  are disallowed. The options listed below for each installer will raise an `OnionArgumentError`:
  - pip:
    - `-h`, `--help`
    - `-r`, `--requirement`
    - `-V`, `--version`


### The `davos` Config
The `davos` config object stores options and data that affect how `davos` behaves. After importing `davos`, the config 
instance (a singleton) for the current session is available as `davos.config`, and its various fields are accessible as 
attributes. The config object exposes a mixture of writable and read-only fields. Most `davos.config` attributes can be 
assigned values to control aspects of `davos` behavior, while others are available for inspection but are set and used 
internally. Additionally, certain config fields may be writable in some situations but not others (e.g. only if the 
Python environment supports a particular feature). Once set, `davos` config options last for the lifetime of the 
interpreter (unless updated); however, they do *not* persist across interpreter sessions. A full list of `davos` config 
fields is available [below](#config-reference):

#### <a name="config-reference"></a>Reference
| Field | Description | Type | Writable? |
| --- | --- | --- | --- |
| `active` | Whether the `davos` parser should be run 

#### <a name="top-level-functions"></a>Top-level Functions
`davos` also provides a few convenience for reading/setting config values:
- **`davos.activate()`**
  Activate the `davos` parser, enable the `smuggle` keyword, and inject the `smuggle()` function into the namespace. 
  Equivalent to setting `davos.config.active = True`.

- **`davos.deactivate()`**
  Deactivate the `davos` parser, disable the `smuggle` keyword, and remove the name `smuggle` from the namespace if (and 
  only if) it refers to the `smuggle()` function. If `smuggle` has been overwritten with a different value, the variable 
  will not be deleted. Equivalent to setting `davos.config.active = False`.

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

## Examples
- smuggle specific version
- smuggle package from VCS
- smuggle package from local dir
- smuggle editable package
- smuggle package with extra requirements
- smuggle latest version fo package
### Valid Syntaxes
## How it works


## Additional Notes
- <a name="notes-installer-opts"></a>**Installer options that affect `davos` behavior**
- <a name="notes-c-extensions"></a>**Smuggling packages with C-extensions**

  Some Python packages that rely heavily on custom data types implemented via 
  [C-extensions](https://docs.python.org/3.9/extending/extending.html) (e.g., `numpy`, `pandas`) dynamically generate 
  modules defining various C functions and data structures, and link them to the Python interpreter when they are first 
  imported. Depending on how these objects are initialized, they may not be subject to normal garbage collection, and 
  persist despite their reference count dropping to zero. This can lead to unexpected errors when reloading the Python 
  module that creates them, particularly if their dynamically generated source code has been changed (e.g., because the 
  reloaded package is a different version).
  
  This can occasionally affect `davos`'s ability to `smuggle` a new version of a package (or dependency) that was 
  previously `import`ed. To handle this, `davos` first checks each package it installs against 
  [`sys.modules`](https://docs.python.org/3.9/library/sys.html#sys.modules). If a different version has already been 
  loaded by the interpreter, `davos` will attempt to replace it with the requested version (in the vast majority of 
  cases, this is not a problem). However, if this fails due to a C-extension-related issue, `davos` will reinstate the 
  old package version _in memory_, while replacing it with the new package version _on disk_.    
  🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥
  **describe behavior after implementing option to trigger restart & rerun cells above**
  
[comment]: <> (  In a Jupyter/Colbab )

[comment]: <> (  notebook, `davos` will prompt you to restart the kernel while allowing the remaining code in the current cell to )

[comment]: <> (  execute. )
  
[comment]: <> (  This way:)

[comment]: <> (    - the `smuggle` statement finishes executing without error)

[comment]: <> (    - )

[comment]: <> (    - the next time the interpreter is launched, the `smuggle`d version will be used)

- <a name="notes-vcs-smuggle"></a>**Smuggling packages from version control systems**
  - To `smuggle` a package from a local or remote VCS URL, you must specify `pip` (i.e., not `conda`) as the  
    [installer](#smuggle-statement-syntax), as only `pip` supports VCS installation.
  - The first time during an interpreter session that a given package is installed from a VCS URL, it is assumed not to 
    be present locally, and is therefore freshly installed. `pip` clones non-editable VCS repositories into a temporary 
    directory, installs them with setuptools, and then immediately deletes them. Since no information is retained about 
    the state of the repository at installation, it is impossible to determine whether an existing package satisfies the 
    state (branch, commit hash, etc.) requested for `smuggle`d package.

[comment]: <> (- As with _all_ code, you should use caution when running Python code containing `smuggle` statements that was not written by you or someone you know. )
