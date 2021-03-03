# Introduction and usage

`Davos` provides Python with a single command, `smuggle`, which is like a quick (and often dirty) wrapper for `import`.  Whereas you cannot `import` a library that hasn't been installed yet, you can easily `smuggle` a not-yet-installed library:

```python
from davos import smuggle
smuggle('seaborn', alias='sns') #installs seaborn if needed!

#now you can use seaborn as if you had imported it the "normal" way
titanic = sns.utils.load_dataset('titanic')
sns.barplot(data=titanic, x='class', y='survived', hue='sex', palette=sns.light_palette('seagreen'))
```
# Installation

You can install `davos` with `pip` as follows:

```bash
pip install davos
```

# Origin of the name

The package name is inspired by [Davos Seaworth](https://gameofthrones.fandom.com/wiki/Davos_Seaworth), a famous smuggler from the [Song of Fire and Ice](https://en.wikipedia.org/wiki/A_Song_of_Ice_and_Fire) series by [George R. R. Martin](https://en.wikipedia.org/wiki/George_R._R._Martin).
