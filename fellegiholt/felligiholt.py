from random import random
from typing import Iterable, Mapping

import pandas as pd
from pulp import LpVariable, LpInteger, LpMinimize, LpProblem, lpSum

from datarules import Check
from .rewrite_linear import rewrite_condition, BIG, LpDict


class FelligiHolt:
    def __init__(self, checks: Iterable[Check]):
        self.pvars = LpDict()
        self.rule_constraints = list(convert_checks(checks, self.pvars))

    def run(self, df, on_error=None):
        errors = []
        for index, row in df.iterrows():
            row_result, row_errors = self._run_row(df, index, row, on_error=on_error)
            errors.append(row_errors)

        # TODO Return result class instead
        return pd.DataFrame(errors, index=df.index)

    def _run_row(self, df, index, row: Mapping, on_error=None):
        model = self._setup_row(row)
        model.solve()
        model_outcome = {var.name: var.value() for var in model.variables()}
        model_errors = {k.removesuffix("_error"): v >= 0.5 for k, v in model_outcome.items() if k.endswith("_error")}
        model_result = {k: v for k, v in model_outcome.items() if k in row}

        if on_error == "remove":
            for k, v in model_errors:
                df.loc[index, k] = pd.NA
        elif on_error == "replace":
            for k, v in model_result:
                df.loc[index, k] = v

        return model_result, model_errors


        # errors = {}
        # # result = {}
        # # n_errors = 0
        # # variables
        #
        # # for var in model.variables():
        # #     if var.name.endswith("_error"):
        # #         name = var.name.removesuffix("_error")
        # #         errors[name] = var.value() >= .5
        # #     elif var.name in row:
        # #         result[var.name] = var.value()
        #
        # return n_errors
        # return result, errors

    def _setup_row(self, row):
        objective, row_constraints = self._encode_row(row)
        model = LpProblem('Row', sense=LpMinimize)
        model += objective
        for r in self.rule_constraints:
            model += r
        for r in row_constraints:
            model += r
        return model

    def _encode_row(self, row):
        target = []
        constraints = []
        for varname, value in row.items():
            var = self.pvars[varname]
            errorvar = LpVariable(name=varname + "_error", lowBound=0, upBound=1, cat=LpInteger)
            target.append(errorvar * (1 + random() / 2))
            constraints += [(var <= value + errorvar * BIG, varname + "_ub"),
                            (var >= value - errorvar * BIG, varname + "_lb")]
        return lpSum(target), constraints


def convert_checks(checks: Iterable[Check], pvars):
    converted_checks = []
    for check in checks:
        try:
            expression = check.test.expression
            constraints = rewrite_condition(expression, pvars)
        except (TypeError, AttributeError):
            print(f"Unable to convert {check}")
        else:
            print("Successfully converted: ", check)
            for i, constraint in enumerate(constraints):
                converted_checks.append((constraint, check.name + f"_{i}"))
    return converted_checks
