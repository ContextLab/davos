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
 - name: Paxton C. Fitzpatrick
   orcid: 0000-0003-0205-3088
   affiliation: 1
 - name: Jeremy R. Manning^[corresponding author]
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

The `davos` Python package provides a toolkit for installing and managing packages at runtime within IPython
notebook environments [@PereGran07] including Jupyter notebooks [@KluyEtal16], JupyterLab, and Google Colaboratory.

Importing `davos` enables an additional Python keyword: `smuggle`. The `smuggle` statement can be used as a drop-in replacement for the
built-in `import` statement to load libraries, modules, and other objects into the current namespace. However, whereas 
`import` will fail if the requested package is not installed locally, `smuggle` statements can handle missing 
packages on-the-fly. If a to-be-smuggled package does not exist in the local environment, `davos` installs it, 
make its contents visible to Python's import machinery, and load it into the namespace for immediate use.

The `davos` package also defines a special type of inline comment called an "*onion comment*" that can be added to a line containing 
a `smuggle` statement to customize its behavior and provide additional, more complex functionality. Onion comments 
follow a simple syntax based on the type comment format introduced in PEP 484 [@vanREtal14], and allow the user to customize 
when and how specific packages are installed from the Python Package Index (PyPI), using wrapped calls to `pip`.

Because onion comments can be used to make `smuggle` statements version-sensitive, `davos` provides a powerful way of
creating fully contained shareable workflows within a single iPython notebook.  In some cases, this can obviate the need
for constructing containerized or virtualized environments (e.g., using [Docker](https://www.docker.com/), [Singularity](https://sylabs.io/singularity/), or [conda](https://docs.conda.io/en/latest/)).

For example, `davos` enables users to specify specific package versions (and even specific VCS revisions, such as git commit
hashes) of to-be-smuggled packages.  When `smuggle` statements are called multiple times within the same notebook (e.g., with
different onion comments), multiple versions of the same package may be used within a single interpreter session.  Although
the current version of `davos` is already fully usable and feature-complete, future extensions of the package could enable
use of the `smuggle` keyword within "vanilla" (non-interactive) Python scripts, and/or support of alternative package managers
such as `conda`.

# Statement of Need

Modern open science practices often entail sharing code and data to enable scientists to reproduce and extend each others' work.
As of the time of writing, Python is already one of the most widely used scientific programming languages, and its user base
is expanding rapidly.  A centerpiece of the Python ecosystem is a powerful and extensive data science toolkit designed to facilitate
rapid development and collaboration.  These tools include platforms for interactive development (e.g., Project 
Jupyter [@PereGran07;@KluyEtal16] and Google Colaboratory), packages for data manipulation (e.g., `NumPy` [@HarrEtal20], 
`SciPy` [@VirtEtal20], `Pandas` [@McKi10]),  packages for data visualization (e.g., `Matplotlib` [@Hunt07], `seaborn` [@Wask21]), and
myriad others.

One downside of the rapidly growing Python ecosystem is that different versions of the same software package can behave differently
as syntax changes are introduced, bugs are introduced or fixed, features are implemented or removed, support for different versions of
Python is added or dropped, and so on.  This instability can be at odds with the goal of producing reproducible workflows that remain
usable across different development environments and over time.  Through its `smuggle` keyword and onion comments, the `davos` package
improves the stability of Python-based workflows by providing a convenient means of precisely controling and manipulating the environment
in which specific code is executed.

# References
