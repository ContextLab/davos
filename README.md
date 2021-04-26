<h1 align="center">davos</h1>

🟥🟥🟥 add badges 🟥🟥🟥

🟥🟥🟥 add logo 🟥🟥🟥

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
package without installing it first_. A special type of comment (called an [**onion**](#the-onion-comment)) may also be 
added after a `smuggle` statement, allowing you to _`smuggle` specific package versions_ and fully control installation 
of missing packages.

To enable the `smuggle` keyword, simply `import davos`:

```python
import davos

# pip-install numpy if needed
smuggle numpy as np  # pip: numpy==1.20.2

# the smuggled package is fully imported and usable
arr = np.arange(15).reshape(3, 5)
# and the onion comment guarantees the desired version!
assert np.__version__ == '1.20.2'
```

## Table of contents
- [Installation](#installation)
- [Usage](#usage)
    - [Overview](#overview)
    - [The `smuggle` Statement](#the-smuggle-statement)
    - [The Onion Comment](#the-onion-comment)
    - [Enabling & Disabling `davos`](#enabling--disabling-davos)
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

## Usage
### Overview
The primary way to use `davos` is via [the `smuggle` statement](#the-smuggle-statement), which is made available 
throughout your code simply by running `import davos`. Like 
[the built-in `import` statement](https://docs.python.org/3/reference/import.html), the `smuggle` statement is used to 
load code from another package or module into the current namespace. The main difference between the two is in how they 
handle missing packages and package versions.

#### Smuggling Missing Packages
`import` requires that packages be installed _before_ the start of the interpreter session. If you attempt to `import` a 
package that cannot be found locally, Python will raise a 
[`ModuleNotFoundError`](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError) (or
[`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError) prior to Python 3.6), and you will have 
to install the package, restart the interpreter to make the new package available, and rerun your code in full.

`smuggle`, however, can handle missing packages on the fly. If you `smuggle` a package that isn't installed locally, 
`davos` will install it, immediately make its contents accessible to the current interpreter's
[import machinery](https://docs.python.org/3.9/reference/import.html), and load the package or specific name(s) into the 
local namespace for use. Optionally, an inline [onion comment](#the-onion-comment) may be added after a `smuggle` 
statement to customize how `davos` will install the package, if it is not found locally.

#### Smuggling Specific Package Versions
You can also use an [onion comment](#the-onion-comment) to make a `smuggle` statement version-sensitive. 

Python does not provide a straightforward, reliable way to ensure a particular version of a package is used at runtime. 
While many packages expose their version information via a `__version__` attribute (see
[PEP 396](https://www.python.org/dev/peps/pep-0396/)) which could be used to manually check the package's version 
_after_ importing it, many others do not support this (and even more don't in older versions). Even in cases where 
validating package versions this way _would_ be possible, it would require writing a potentially large amount of extra 
code, and _still_ force you to manually install the correct package version; restart the interpreter; and rerun your 
code in full for every check that fails. Additionally, for packages installed through a version control system (e.g., 
GitHub), this would be insensitive to differences between revisions (e.g., commits) within the same semantic version.

`davos` solves these issues by allowing you to constrain each `smuggle`d to a specific version or range of 
acceptable versions. You can do this simply by placing a 
[version specifier](https://www.python.org/dev/peps/pep-0440/#version-specifiers) in an 
[onion comment](#the-onion-comment) next to the corresponding smuggle statement:
```python
smuggle foo             # pip: foo==1.2.3
from bar smuggle baz    # pip: bar>=4.5,<5.0
```
In this example, the first line will load the package "`foo`" into the local namespace, just as "`import foo`" would.
`davos` will first check whether `foo` is installed locally, and if so, whether the installed version exactly matches 
`1.2.3`. If `foo` is not installed, or the installed version is anything other than `1.2.3`, `davos` will use the 
specified _installer_, `pip`, to install `foo==1.2.3` before loading the package. 

Similarly, the second line will load the name "`baz`" from the package "`bar`" analogously to "`from baz import bar`". A 
local `bar` version of `4.7.2` would be used, but a local version of `5.3.1` would cause `davos` to install the package 
by running the command `pip install bar>=4.5,<5.0`. 

In either case, the imported versions will fit the constraints specified in their [onion comments](#the-onion-comment), 
and the next time `foo` and `bar` are smuggled with the same constraints, valid local installations will be found.
With [a few exceptions](#limit-c-ext), this will work _even if the packages were previously imported._


#### Use Cases
### The `smuggle` Statement
#### Purpose
#### Syntax
The `smuggle` statement is designed to be used in place of 
[the built-in `import` statement](https://docs.python.org/3/reference/import.html) and shares
[its full syntactic definition](https://docs.python.org/3/reference/simple_stmts.html#the-import-statement):
```ebnf
smuggle_stmt     ::=  "smuggle" module ["as" identifier] ("," module ["as" identifier])*
                     | "from" relative_module "smuggle" identifier ["as" identifier]
                     ("," identifier ["as" identifier])*
                     | "from" relative_module "smuggle" "(" identifier ["as" identifier]
                     ("," identifier ["as" identifier])* [","] ")"
                     | "from" module "smuggle" "*"
module          ::=  (identifier ".")* identifier
relative_module ::=  "."* module | "."+
```
In simpler terms, any valid syntax for `import` is also a valid syntax for `smuggle` (`smuggle foo`, `from foo.bar 
smuggle baz as qux`, etc.). See [below](#valid-syntaxes) for a full list of valid forms.


### The Onion Comment
#### Purpose
#### Syntax

### Enabling & Disabling `davos`

## Examples
### Common use cases
### Valid Syntaxes

## How it works
### Google Colab
### Jupyter Notebooks
### Python scripts

## FAQ

## Limitations & Final Notes

- <a name="limit-c-ext"></a>**limitation about C extensions here**
- As with _all_ code, you should use caution when running Python code containing `smuggle` statements that was not written by you or someone you know. 



Once you import the `davos` library, you can use `smuggle` as a stand in keyword-like object anywhere you would have otherwise used `import`.  Any of the following will work:
```python
smuggle pickle                             # built-in modules
from matplotlib smuggle pyplot as plt      # "from" keyword, renaming sub-modules using "as"
from scipy.spatial.distance smuggle cdist  # import sub-modules using dot notation
smuggle os, sys                            # comma notation
smuggle pandas as pd, numpy as np          # comma notation with renaming using "as"
```