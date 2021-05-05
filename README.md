<div align="center">
  <h1>davos</h1>
  <img src="https://user-images.githubusercontent.com/26118297/116332586-0c6ce080-a7a0-11eb-94ad-0502c96cf8ef.png" width=250/>
</div>

🟥🟥🟥 add badges 🟥🟥🟥


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
    - [Simplify Sharing Reproducible Code & Coding Environments](#simplify-sharing-reproducible-code--coding-environments)
    - [Guarantee your code always uses the latest version, release, or revision](#guarantee-your-code-always-uses-the-latest-version-release-or-revision)
    - [Compare behavior across package versions](#compare-behavior-across-package-versions)
- [Usage](#usage)
  - [The `smuggle` Statement](#the-smuggle-statement)
    - [Syntax](#smuggle-statement-syntax)
    - [Rules](#smuggle-statement-rules)
  - [The Onion Comment](#the-onion-comment)
    - [Syntax](#onion-comment-syntax)
    - [Rules](#onion-comment-rules)
  - [Customizing `davos` Behavior](#customizing-davos-behavior)
- [Examples](#examples)
- [How it works](#how-it-works)
- [FAQ](#faq)
- [Limitations & Final Notes](#limitations--final-notes)


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
from sklearn.decomposition import pca    # pip: scikit-learn
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

You can also ensure the state of a packages matches a specific VCS branch, revision, ref, or release. For example:
```python
smuggle hypertools as hyp    # pip: git+https://github.com/ContextLab/hypertools.git@36c12fd
```
will load [`hypertools`](https://hypertools.readthedocs.io/en/latest/) (aliased as "`hyp`"), as the package existed 
[on GitHub](https://github.com/ContextLab/hypertools), at commit 
[36c12fd](https://github.com/ContextLab/hypertools/tree/36c12fd). The general format for VCS references in 
[onion comments](#the-onion-comment) follows that of the 
[`pip-install`](https://pip.pypa.io/en/stable/cli/pip_install/#vcs-support) command. See the 
[limitations section on smuggling from VCS](limitation-vcs-smuggle) for additional notes.

With [a few exceptions](#limitation-c-extensions), smuggling a specific package version will work _even if the package 
has already been imported_.


### Use Cases
#### Simplify sharing reproducible code & coding environments
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
statements with `smuggle` statements, add package versions in onion comments, and let `davos` take care of the rest. 
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
useful tool for comparing behavior across multiple versions of the same package, all within the same runtime:
```python
data = list(range(10))

smuggle mypkg                    # pip: mypkg==0.1
result1 = mypkg.my_func(data)

smuggle mypkg                    # pip: mypkg==0.2
result2 = mypkg.my_func(data)

smuggle mypkg                    # pip: git+https://github.com/MyOrg/mypkg.git
result3 = mypkg.my_func(data)

print(result1 == result2 == result3)
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


In simpler terms, any valid syntax for `import` is also a valid syntax for `smuggle` (`smuggle foo`, `from foo.bar 
smuggle baz as qux`, etc.). See [below](#valid-syntaxes) for a full list of valid forms.


#### <a name="smuggle-statement-rules"></a>Rules
- Like `import` statements, `smuggle` statements are whitespace-insensitive, unless a lack of whitespace between two 
  tokens would cause them to be interpreted as a different token:
  ```python
  from   os    . path    smuggle  dirname     ,join       as    opj    # valid
  from os.path smuggle dirname, join asopj                             # invalid
  ```
- Any context that would cause an `import` statement _not_ to be executed will do the same to a `smuggle` statement:
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
  [Colaboratory](https://colab.research.google.com/)) `smuggle` statements always load names into the global namespace:
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
  type(datetime)                               # executed
  ```
  However, this does not affect plain Python scripts:
  ```python
  # example.py
  import davos
  
  
  def smuggle_example():
      smuggle datetime
  
  
  smuggle_example()
  type(datetime)                               # raises NameError
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
[VCS-based](https://pip.pypa.io/en/stable/cli/pip_install/#vcs-support) installation, while `conda` supports 
[additional specifier characters](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#examples) 
and three-part 
[package match specifications](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications).

Less formally, an onion comment simply consists of two parts, separated by a colon: 
1. the name of the installer program
2. the arguments passed to the program's "install" command

Thus, you can essentially think of writing an onion comment as taking the full shell command you would run to install 
the package, and replacing "_install_" with "_:_". For instance, the command:
```
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


#### <a name="onion-comment-rules"></a>Rules
onion comment rules


### Customizing `davos` Behavior
## Examples
### Valid Syntaxes
## How it works
### Google Colab
### Jupyter Notebooks
### Python scripts
## FAQ


## Limitations & Final Notes
- <a name="limitation-c-extensions"></a>**limitation about C extensions here**
- <a name="limitation-vcs-smuggle"></a>**limitations about packages that specify vcs commits**
  - **installer must be pip**
  - **non-editable VCS installs always freshly installed**

[comment]: <> (- As with _all_ code, you should use caution when running Python code containing `smuggle` statements that was not written by you or someone you know. )



Once you import the `davos` library, you can use `smuggle` as a stand in keyword-like object anywhere you would have otherwise used `import`.  Any of the following will work:
