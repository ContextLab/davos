# Introduction

Davos provides Python with a single command, `smuggle`, which is like a quick (and often dirty) wrapper for `import`.  Whereas you cannot `import` a library that hasn't been installed yet, you can easily `smuggle` a not-yet-installed library:

```python
from davos import smuggle
smuggle('seaborn', alias='sns') #installs seaborn if needed!

#now you can use seaborn as if you had imported it the "normal" way
titanic = sns.utils.load_dataset('titanic')
sns.barplot(data=titanic, x='class', y='survived', hue='sex', palette=sns.light_palette('seagreen'))
```
