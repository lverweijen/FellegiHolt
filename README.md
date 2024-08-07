Constrain a dataset to a set of given constraints.

## Main idea

The original idea is described in [[1]](#1).

- Convert checks to linear constraints (so it can be solved as a MIP)
- For each row in dataframe:
  - Find the minimal set of variables that need to be adjusted to make the row satisfy all constraints.
  - Remove or replace (set to `pd.NA`) these faulty variables.
- Impute missing variables (out of scope)
  
A more practical description can be found in [this vignette](https://cran.r-project.org/web/packages/errorlocate/vignettes/inspect_mip.html).

## Example

```python
# Example shamelessly copied and converted from https://github.com/data-cleaning/errorlocate/blob/master/README.Rmd
import pandas as pd
from datarules import Check
from uneval import quote as q

from fellegiholt import ErrorDetector

checks = [
  Check(q.profit == q.turnover - q.cost),
  Check(q.cost >= 0.6 * q.turnover),
  Check(q.cost >= 0),
  Check(q.married >> (q.age >= 16)),
]

df = pd.DataFrame([
  {'profit': 750, 'cost': 125, 'turnover': 200},
  {'married': True, 'age': 15},
  {'married': False, 'age': 15},
  {'married': True, 'age': 16},
  {'married': False, 'age': 16},
])

detector = ErrorDetector(checks)
report = detector.run(df, on_error="remove")

print("df = {!r}".format(df))
print("report.get_errors() = {!r}".format(report.get_errors()))
```

Output:

```python
# df    
   profit   cost  turnover married   age
0     NaN  125.0     200.0     NaN   NaN
1     NaN    NaN       NaN    <NA>  15.0
2     NaN    NaN       NaN   False  15.0
3     NaN    NaN       NaN    True  16.0
4     NaN    NaN       NaN   False  16.0
# report.get_errors()
      profit  married
   0    True    False
   1   False     True
   2   False    False
   3   False    False
   4   False    False
```

## Limitations

- This is only a proof of concept. Not stable, not mature, not well tested.
- In case the problem is infeasible, nothing happens. This should probably be handled.
- if/else, or/and don't always work correctly. It's difficult to get numeric stability.

## See also

An R-implementation (which is more mature than this and should probably be used instead) can be found on:
https://github.com/data-cleaning/errorlocate


## References
<a id="1">[1]</a> 
I. P. Fellegi and D. Holt (1976)
A Systematic Approach to Automatic Edit and Imputation
Journal of the American Statistical Association 71(353), 17-35
