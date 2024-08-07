# Example shamelessly copied and converted from https://github.com/data-cleaning/errorlocate/blob/master/README.Rmd
import pandas as pd
from datarules import Check
from uneval import quote as q

from fellegiholt import ErrorDetector

checks = [
    Check(q.profit == q.turnover - q.cost, name="addition_profit", tags=["hard"]),
    Check(q.cost >= 0.6 * q.turnover, name="cost_gt_turnover", tags=["soft"]),
    Check(q.cost >= 0, name="positive_costs", tags=["hard"]),
    Check(q.married >> (q.age >= 16), name="eligible_for_marriage", tags=["hard"]),
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
