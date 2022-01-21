---
title: '`davos`: The Python package smuggler'
tags:
 - Python
 - Jupyter Notebook
 - JupyterLab
 - Google Colab
 - reproducibility
 - package management
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
date: 20 January 2022
bibliography: paper.bib
link-citations: true
---


# Summary

`davos` is a Python package for creating self-managing, reproducible workflows
that specify dependencies directly within their code and install packages as
needed at runtime. The `davos` package was developed to simplify sharing
research-related code including data analyses, tutorials, and demos by allowing
users to distribute their code and environment together in a single,
ready-to-run Jupyter notebook [@KluyEtal16].

Importing `davos` enables an additional Python keyword: `smuggle`. The `smuggle`
statement can be used as a drop-in replacement for the built-in `import`
statement to load libraries, modules, and other objects into the current
namespace. However, whereas `import` will fail if the requested package is not
installed locally, `smuggle` statements can handle missing packages on the fly.
If a smuggled package does not exist in the local environment, `davos` will
install it, make its contents visible to Python's `import` machinery, and load
it into the namespace for immediate use.

For greater control over the behavior of `smuggle` statements, `davos` defines 
an additional construct called the *onion comment*. An onion comment is a 
special type of inline comment that can be placed on a line containing a 
`smuggle` statement to customize how `davos` determines whether and how the
smuggled package should be installed. Onion comments follow a simple syntax
based on the type comment syntax introduced in PEP 484 [@vanREtal14] and are
designed to make controlling installation via `davos` intuitive and familiar. To
construct an onion comment, simply provide the name of the installer program
(e.g., `pip`) and the same arguments one would use to install the package as
desired manually via the command line:

![](snippets/snippet1.pdf)

Onion comments are also useful for smuggling a package whose distribution name
(i.e., the name used when installing it) is different from its top-level module
name (i.e., the name used when importing it):

![](snippets/snippet2.pdf)

However, the most powerful use of the onion comment is making `smuggle`
statements *version-sensitive*. Adding a [version
specifier](https://www.python.org/dev/peps/pep-0440/#version-specifiers) to an
onion comment will cause `davos` to search for the smuggled package in the local
environment (as usual), and if it is found, further check whether the
installed version satisfies the given constraint(s). If either check fails,
`davos` will install and use a suitable version of the package:

![](snippets/snippet3.pdf)

It is also possible to `smuggle` a specific VCS reference (e.g., a git branch,
commit, tag, etc.):

![](snippets/snippet4.pdf)

Additionally, certain arguments can be added to skip searching the local
environment altogether, and instead always install a fresh version of the
package:

![](snippets/snippet5.pdf)

Because `davos` parses onion comments at runtime, required packages are
validated and installed in a just-in-time manner. Thus, it is possible in most
cases to `smuggle` a specific package version or revision even if a different
version has already been loaded. This enables more complex use cases that take
advantage of multiple versions of a package within a single interpreter session
(e.g., loading an unstable development version only when necessary to use a new
feature, comparing performance across versions for demos or regression testing,
etc.).

Finally, `davos` provides a simple, high-level interface that allows users to
disable, re-enable, and configure its functionality at any point throughout
their code. `davos` currently supports IPython [@PereGran07] notebook
environments including Jupyter notebooks [@KluyEtal16], JupyterLab
[@GranGrou16], Google Colaboratory, Binder [@RagaWill18], and IDE-based notebook
editors. Potential future directions include extending `davos` for use in
"vanilla" (i.e., non-interactive) Python scripts and adding support for
installation via alternative package managers such as `conda`. The `davos`
package is currently being used in a number of ongoing projects, as well as
online demos for [*Storytelling with
Data*](https://github.com/ContextLab/storytelling-with-data) [@Mann21b\; an open
course on data science, visualization, and communication] and `abstract2paper`
[@Mann21a\; a toy application of
[GPT-Neo](https://github.com/EleutherAI/gpt-neo)]. A more extensive guide to
using `davos`, additional examples, and implementation details are available
[here](https://github.com/ContextLab/davos).


# Statement of Need

Modern open science practices encourage sharing code and data to enable others
to explore, reproduce, and build on existing work. Scientists, researchers, and
educators may seek to share research-related code with collaborators, students, the research
community, or the general public. Python is among the most widely used and
fastest-growing scientific programming languages [@MullEtal15]. In addition to
the language's high-level, accessible syntax and large standard library, the
Python ecosystem offers a powerful and extensive data science toolkit designed
to facilitate rapid development and collaboration, including platforms for
interactive programming [e.g., Project Jupyter, @KluyEtal16\; Google
Colaboratory], community-maintained libraries for data manipulation [e.g.,
`NumPy`, @HarrEtal20; `SciPy`, @VirtEtal20; `Pandas`, @McKi10] and
visualization [e.g., `Matplotlib`, @Hunt07; `seaborn`, @Wask21], and myriad
other tools.

However, one impediment to sharing and reproducing computational work
implemented in Python is that different versions of a given package or library
can behave differently, use different syntax, add or drop support for specific
functions or other libraries, address (or introduce) bugs, and so on. These
challenges are true to some extent in any language or ecosystem, but they have a
particular impact on the Python community due to its unusually rapid growth
relative to other languages. Ensuring stable and reproducible results across
users typically requires ensuring that the same versions of each library are
installed. One approach is to use containerized or virtualized environments
(e.g., using [Docker](https://www.docker.com/),
[Singularity](https://sylabs.io/singularity/), or
[conda](https://docs.conda.io/en/latest/)) that are effectively cordoned off
from the user's primary Python installation. Configuration files may be used
alongside these tools to construct environments that guarantee (within limits)
the same or similar functionality across systems. However, a downside to
relying on this approach is that it is highly resource intensive. For example,
distributing research code that relies on a particular Docker image to run
correctly requires the authors to distribute additional configuration files and
instructions alongside their main code. Users must then download or build the
image on their machine, which uses additional time and storage.

`davos` provides an alternative way of ensuring stable functionality of iPython
notebooks across users that is lightweight and contained entirely within the
notebook file itself. All setup and configuration of packages needed to run the
code in the notebook, including ensuring that the correct version of each
package is utilized, may be managed by `davos`. Bypassing the need for
the user to set up containers or virtual environments can enable users to run
the notebook quickly and more easily.

A second benefit of using `davos` (either in lieu of or alongside a different
environment management tool) is that `smuggle` statements and onion comments
continue to ensure requirements are satisfied after they are initially
installed. For example, suppose a developer decides to install version 1.0 of
package `x`, a critical library for some code they are working on. If `x`
version 1.1 is a dependency of another package, `y`, then installing package `y`
might overwrite version 1.0 of package `x` with version 1.1. This can lead to
unexpected behavior if versions 1.0 and 1.1 of package `x` differ. To protect
against unexpected behavior, `smuggle` statements and onion comments may be
used to ensure that the expected versions of each library are imported.

# Origin of the Name

The package name is inspired by [Davos
Seaworth](https://en.wikipedia.org/wiki/Davos_Seaworth), a smuggler often
referred to as "the Onion Knight" from the series [*A song of Ice and
Fire*](https://en.wikipedia.org/wiki/A_Song_of_Ice_and_Fire) by [George R. R.
Martin](https://en.wikipedia.org/wiki/George_R._R._Martin).


# References
