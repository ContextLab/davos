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
functions or other libraries, address (or introduce) bugs, and so on. While 
these challenges are present to some extent in any language or ecosystem, they
have a particular impact on the Python community due to its unusually rapid
growth relative to other languages. Ensuring stable and reproducible results
across users typically requires ensuring that shared code is always run with the
same set of versions for each package used. One common approach to solving this
problem is to create containerized or virtualized environments (e.g., using
[Docker](https://www.docker.com/),
[Singularity](https://sylabs.io/singularity/), or
[conda](https://docs.conda.io/en/latest/)) that house fully isolated Python
installations tailored to specific projects. These environments may be
shared publicly as configuration files from which other users may
build identical copies themselves. While effective, one drawback to this 
approach is that it can introduce a level of complexity beyond what is 
warranted for many simpler use cases. For example, distributing research code that relies on a
particular Docker image to run properly not only necessitates extra 
configuration files and setup steps, but requires that both the author and end
user install and navigate additional software that is often more complicated and
resource-intensive than the actual code being shared. These added prerequisites
clash with the simplicity and accessibility that have helped popularize Python 
among researchers, and can create barriers to both contributing to and taking 
advantage of open science.


`davos` provides an alternative way to ensure stable functionality of 
Jupyter notebooks across users and over time that is intuitive, lightweight, and contained 
entirely within the notebook file itself. Using `smuggle` statements and onion 
comments, required packages can be specified directly within the code that uses 
them and automatically installed as they are needed. This offers two 
notable advantages over typical approaches to dependency management. First, it 
simplifies and expedites the process of sharing reproducible workflows by 
eliminating the need for additional configuration files, pre-execution setup, 
and environment management software (aside from `davos` itself). With `davos`, 
analyses, tutorials, and demos can be packaged and shared as "batteries 
included" notebooks that can be downloaded and immediately run, making them more
accessible to less technical users.

Second, `smuggle` statements and onion comments continue to ensure requirements 
are satisfied after they are initially installed. Most dependency specification 
schemes follow a common strategy: required packages and package versions are 
listed in a configuration file (e.g., a `requirements.txt`, `pyproject.toml`, 
`environment.yml`, `Pipfile`, `RUN` instructions in a 
`Dockerfile`, etc.) which is used to install them in a Python environment 
upfront. After this initial setup, however, this method generally does not 
ensure that the specified requirements *remain* installed, allowing them to be easily 
altered&mdash;sometimes inadvertently. This can lead to subtle issues when 
writing reproducible code in such a preconfigured environment. For instance, suppose a 
researcher has implemented a series of analyses using version 1.0 of "Package 
*X*", and later decides to perform an additional analysis that requires installing 
"Package *Y*". If Package *Y* depends on version 1.1 of Package *X*, then
Package *X* will be upgraded to accommodate this new requirement. And if the 
researcher does not notice this change, differences between the two Package *X* 
versions risk introducing bugs into previously written code. Using `davos`, either
in lieu of or alongside a different environment management tool, provides a 
safeguard against this situation. `smuggle` statements and onion comments 
enforce requirements every time they are executed, guaranteeing the expected 
version of each package is always used. This would not only catch and correct 
the unintentional change to Package *X*, but would also allow the researcher to 
choose whether to manually resolve the inconsistency or, if appropriate, 
`smuggle` different versions of the package as necessary.


# Origin of the Name

The package name is inspired by [Davos
Seaworth](https://en.wikipedia.org/wiki/Davos_Seaworth), a smuggler often
referred to as "the Onion Knight" from the series [*A song of Ice and
Fire*](https://en.wikipedia.org/wiki/A_Song_of_Ice_and_Fire) by [George R. R.
Martin](https://en.wikipedia.org/wiki/George_R._R._Martin).


# References
