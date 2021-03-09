# Introduction and usage

The `davos` library provides Python with a single keyword-like object, `smuggle`, which is like a quick (and often dirty) wrapper for `import`.  Whereas you cannot `import` a library that hasn't been installed yet, you can easily `smuggle` a not-yet-installed library:

```python
import davos

smuggle seaborn as sns # installs seaborn if needed!

# now you can use seaborn as if you had imported it the "normal" way
titanic = sns.utils.load_dataset('titanic')
sns.barplot(data=titanic, x='class', y='survived', hue='sex', palette=sns.light_palette('seagreen'))
```

## Other usage options

Once you import the `davos` library, you can use `smuggle` as a stand in keyword-like object anywhere you would have otherwise used `import`.  Any of the following will work:
```python
smuggle pickle                             # built-in modules
from matplotlib smuggle pyplot as plt      # "from" keyword, renaming sub-modules using "as"
from scipy.spatial.distance smuggle cdist  # import sub-modules using dot notation
smuggle os, sys                            # comma notation
smuggle pandas as pd, numpy as np          # comma notation with renaming using "as"
```

## Unsupported stuff

The `smuggle` function cannot automatically resolve package names.  For example, if the `umap-learn` package isn't installed, `smuggle umap` will attempt to `pip install umap` (which is a different library) rather than `pip install umap-learn`.  If the `pip` name and `import` name don't match, you can manually pass a module's `pip` name to `smuggle` as follows:

```python
@pipname('scikit-learn')
smuggle sklearn.decomposition.LatentDirichletAllocation as LDA
```

# Installation

You can install the latest official version of `davos` with `pip` as follows:

```bash
pip install davos
```

To install the cutting (bleeding) edge version directly from git, use:

```bash
pip install git+ssh:https://github.com/ContextLab/davos.git
```

# Origin of the name

The package name is inspired by [Davos Seaworth](https://gameofthrones.fandom.com/wiki/Davos_Seaworth), a famous smuggler from the [Song of Fire and Ice](https://en.wikipedia.org/wiki/A_Song_of_Ice_and_Fire) series by [George R. R. Martin](https://en.wikipedia.org/wiki/George_R._R._Martin).
