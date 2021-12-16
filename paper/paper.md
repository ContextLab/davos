---
title: '`davos`: The Python package smuggler'
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
date: 15 December 2021
bibliography: paper.bib
link-citations: true
---


# Summary

`davos` is a Python package for creating self-managing, reproducible workflows that specify dependencies directly within 
their code and install packages as needed at runtime. The `davos` package was developed to simplify sharing 
research-related code including data analyses, tutorials, and demos by allowing users to distribute their code and 
environment together in a single, ready-to-run Jupyter notebook [@KluyEtal16].

Importing `davos` enables an additional Python keyword: `smuggle`. The `smuggle` statement can be used as a drop-in 
replacement for the built-in `import` statement to load libraries, modules, and other objects into the current 
namespace. However, whereas `import` will fail if the requested package is not installed locally, `smuggle` statements 
can handle missing packages on the fly. If a smuggled package does not exist in the local environment, `davos` 
will install it, make its contents visible to Python's import machinery, and load it into the namespace for immediate 
use.

While the `smuggle` statement can be used on its own, `davos` also defines an additional construct called the "*onion 
comment*" that provides greater control over its behavior along with more complex functionality. An onion comment is a 
special type of inline comment that can be placed on a line containing a `smuggle` statement to customize how `davos` 
determines whether the smuggled package should be installed and, if necessary, installs it. Onion comments follow a 
simple syntax based on the type comment syntax introduced in PEP 484 [@vanREtal14] and are designed to make controlling 
installation via `davos` intuitive and familiar. To construct an onion comment, simply provide the name of the installer 
program (e.g., `pip`) and the same arguments one would use to install the package as desired manually via the command 
line:

![](snippets/snippet1.pdf)

Onion comments are also useful for smuggling a package whose distribution name (i.e., the name used when installing it) 
is different from its top-level module name (i.e., the name used when importing it):

![](snippets/snippet2.pdf)

However, the most powerful use of the onion comment is making `smuggle` statements *version-sensitive*. Adding a 
[version specifier](https://www.python.org/dev/peps/pep-0440/#version-specifiers) to an onion comment will cause `davos`
to search for the smuggled package in the local environment (as usual), and if it exists, additionally check whether 
the installed version satisfies the given constraint(s). If either check fails, `davos` will install and use a suitable 
version of the package:

![](snippets/snippet3.pdf)

It is also possible to `smuggle` a specific VCS reference (e.g., a git branch, commit, tag, etc.):

![](snippets/snippet4.pdf)

Additionally, certain arguments can be added to skip searching the local environment altogether, and instead always 
install a fresh version of the package:

![](snippets/snippet5.pdf)

Because `davos` parses onion comments at runtime, required packages are validated and installed in a just-in-time 
manner. Thus, it is possible in most cases to `smuggle` a specific package version or revision even if a different 
version has already been loaded. This opens the door to more complex use cases that take advantage of multiple versions 
of a package within a single interpreter session (e.g., loading an unstable development version only when necessary to 
use a new feature, comparing performance across versions for demos or regression testing, etc.).

Finally, `davos` provides a simple, high-level interface that allows users to disable, re-enable, and configure its 
functionality at any point throughout their code. `davos` currently supports IPython [@PereGran07] notebook environments 
including Jupyter notebooks [@KluyEtal16], JupyterLab [@GranGrou16], Google Colaboratory, Binder [@RagaWill18], and 
IDE-based notebook editors. Potential future directions include extending `davos` for use in "vanilla" (i.e., 
non-interactive) Python scripts and adding support for installation via alternative package managers such as `conda`. 
The `davos` package is currently being used in a number of ongoing projects, as well as online demos for 
[*Storytelling with Data*](https://github.com/ContextLab/storytelling-with-data) [@Mann21b\; an open course on data 
science, visualization, and communication] and `abstract2paper` [@Mann21a\; a toy application of 
[GPT-Neo](https://github.com/EleutherAI/gpt-neo)]. A more extensive guide to using `davos`, additional examples, and a 
description of how it works are available [here](https://github.com/ContextLab/davos).


# Statement of Need

Modern open science practices encourage sharing code and data to enable others to explore, reproduce and extend existing
work. Researchers may seek to share analyses with collaborators while working on a study, with the public upon its 
completion, or with students in classroom or workshop settings. Python is among the most widely used and fastest-growing 
scientific programming languages [@MullEtal15]. In addition to the language's high-level, accessible syntax and large 
standard library, the Python ecosystem offers a powerful and extensive data science toolkit designed to facilitate rapid 
development and collaboration, including platforms for interactive development [e.g., Project Jupyter, @KluyEtal16\; 
Google Colaboratory], community-maintained libraries for data manipulation [e.g., `NumPy`, @HarrEtal20; `SciPy`, 
@VirtEtal20; `Pandas`, @McKi10] and visualization [e.g., `Matplotlib`, @Hunt07; `seaborn`, @Wask21], and myriad other 
tools. 

However, one challenge posed by the rapidly growing Python ecosystem is that different versions of the same package can 
behave quite differently&mdash;bugs are introduced and fixed, features are implemented and removed, support for Python 
versions is added and dropped, and so on. Thus, Python code whose behavior and outputs need to remain consistent over 
time and across users (e.g., data analyses, tutorials, or demos) are customarily shared alongside a set of fixed 
versions for each package used. This frequently takes the form of a configuration file for a development environment 
(e.g., a [Docker](https://www.docker.com/) image, [Singularity](https://sylabs.io/singularity/) image, or 
[conda](https://docs.conda.io/en/latest/) environment) the end user must build and manage themselves. While powerful,
such tools are often superfluous for simpler needs and add an additional level of complexity that can raise the 
barriers to entry for sharing, exploring, contributing to, and learning from research-related code. For authors, they 
require distributing additional files and setup instructions alongside the code itself. For users, they require 
installing and using additional software that can be cumbersome, resource-intensive, and confusing to navigate without 
prior familiarity.

Instead, `davos` offers a mechanism for defining a set of required Python packages directly within the code that uses 
them. The first improvement this framework affords is the ability to create reproducible workflows that can be shared 
and run without the need for extra configuration files, software, and setup in order to do so. This can expedite 
collaboration between researchers and improve accessibility for less experienced users.

The second advantage to using `davos` is that it helps ensure dependencies *remain* present and stable over time. Most 
requirement specification schemes entail building a development environment in which a particular set of packages and 
versions are initially installed, but not constrained past that point. This can pose unexpected challenges for 
researchers working on data analyses within such a preconfigured environment, as well as anyone with whom their code and 
environment may eventually be shared: it is easy to inadvertently alter the development environment after its initial 
creation. For example, deciding to perform additional analyses or extend existing ones may require installing additional 
packages after the environment has been built to specification. This can trigger easy-to-miss updates to packages used 
in earlier analyses that can go unnoticed and potentially affect their behavior. `davos` provides a 
safeguard against this situation by continuing to enforce pinned package versions each time a `smuggle` statement is 
run, ensuring that any accidental changes to the environment are caught and will not affect reproducibility.


# Origin of the Name

The package name is inspired by [Davos Seaworth](https://en.wikipedia.org/wiki/Davos_Seaworth), a smuggler often 
referred to as "the Onion Knight" from the series
[*A song of Ice and Fire*](https://en.wikipedia.org/wiki/A_Song_of_Ice_and_Fire) by 
[George R. R. Martin](https://en.wikipedia.org/wiki/George_R._R._Martin).


# References
