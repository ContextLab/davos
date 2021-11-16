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
link-citations: true
---


# Summary

`davos` is a Python package that allows you to install and manage other packages at runtime. 

Importing `davos` enables an additional Python keyword: `smuggle`. The `smuggle` statement can be used just like the
built-in `import` statement to load libraries, modules, and other objects into the current namespace. However, whereas 
`import` will fail if the requested package is not installed locally, `smuggle` statements can handle missing 
packages on the fly. If a smuggled package does not exist in your local environment, `davos` will install it for you, 
make its contents visible to Python's import machinery, and load it into the namespace for immediate use.

`davos` also defines a special type of inline comment called an "*onion comment*" that can be added to a line containing 
a `smuggle` statement to customize its behavior and provide additional, more complex functionality. Onion comments 
follow a simple syntax based on the type comment format introduced in PEP 484 [@vanREtal14], and allow you to customize 
installation of missing packages using the same arguments (and shell syntax) as you would when installing packages 
manually via the command line. `davos` parses onion comments at runtime and adapts its behavior based on the options 
provided&mdash;for instance, `pip`'s "`--ignore-installed`" flag will cause `davos` to skip checking whether the smuggled 
package exists locally before installing it. Onion comments are also useful when smuggling a package whose distribution 
name (i.e., the name used when installing it) is different from its top-level module name (i.e., the name used when 
importing it).

However, possibly the most powerful use of the onion comment is *making `smuggle` statements version-sensitive*. If an 
onion comment contains a version specifier, `davos` will check both whether the smuggled package is installed locally 
*and* whether the installed version satisfies the given ___________________. The ability to `smuggle` specific package 
versions (and even specific VCS revisions, i.e., git commits) allows for entirely new Python workflows, including 
specifing dependencies directly within your code, quickly validating requirements at execution, and even using multiple 
versions of the same package within a single interpreter session.

The `davos` package provides a simple, high-level interface to disable and re-enable its functionality at any point 
throughout your code, as well as the `davos.config` object for inspecting and configuring various default behaviors. 
`davos` supports IPython notebook environments [@PereGran07] including Jupyter notebooks [@KluyEtal16], JupyterLab, and 
Google Colaboratory, and installs packages from the Python Package Index (PyPI) via `pip`. Future directions include 
extending `davos` for use with "vanilla" (i.e., non-interactive) Python scripts and alternative package managers such as `conda`.


# Statement of Need

Open Science practices entail sharing data analysis code throughout the research process: with collaborators while working on 
a project, with the public upon its completion, and with students in classroom or tutorial settings. The Python 
programming language is an extremely popular choice for working with scientific data. In addition to the language's 
high-level, accessible syntax, the Python ecosystem offers numerous third-party tools that make working with scientific 
data easier, from platforms for interactive development (e.g., Project Jupyter [@PereGran07;@KluyEtal16], Colaboratory) to 
powerful, community-driven packages for data manipulation (e.g., `NumPy` [@HarrEtal20], `SciPy` [@VirtEtal20], `Pandas` 
[@McKi10]) and visualization (e.g., `Matplotlib` [@Hunt07], `seaborn` [@Wask21]).

However, different versions of the same software package can often behave quite differently---bugs are introduced and 
fixed, features are implemented and removed, support for different Python versions is added and dropped, etc. Thus, 
Python code that is meant to be _reproducible_ (such as data analyses) is commonly shared alongside a set of fixed 
versions for each package used. And since there is no Python-native way to specify package versions at runtime, this 
typically takes the form of a specification file for a development environment (e.g., a 
[Docker](https://www.docker.com/) container or [conda](https://docs.conda.io/en/latest/) environment) the user must 
build themselves. This 

This can create a barrier for users, 


# ALPHABETIZE PAPER.BIB

# References
