<h1 align="center">davos</h1>

## badges here

## logo here

> _Someone once told me that the night is dark and full of terrors. And tonight I am no knight. Tonight I am Davos the 
smuggler again. Would that you were an onion._
<div align="right">
    &mdash;<a href="https://gameofthrones.fandom.com/wiki/Davos_Seaworth">Ser Davos Seaworth</a>
    <br>
    <a href="https://gameofthrones.fandom.com/wiki/A_Clash_of_Kings"><i>A Clash of Kings</i></a> by
    <a href="https://gameofthrones.fandom.com/wiki/George_R._R._Martin">George R. R. Martin</a>
</div>


The `davos` library provides Python with an additional keyword: **`smuggle`**. 

`smuggle` statements work just like standard `import` statements with one major addition: *you can `smuggle` a package 
without installing it first*. In addition, a special type of inline comment (called an **onion**) may be added after a
`smuggle` statement to constrain the imported package's version or pass arguments for installing a missing package.

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
