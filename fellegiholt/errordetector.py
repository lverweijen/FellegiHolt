from random import random
from typing import Iterable, Mapping

import pandas as pd
from datarules import Check
from pulp import LpVariable, LpInteger, LpMinimize, LpProblem, lpSum

from .rewrite_linear import rewrite_condition, BIG, LpDict

ERROR_SUFFIX = "_error"


class ErrorDetector:
    def __init__(self, checks: Iterable[Check]):
        self.pvars = LpDict()
        self.rule_constraints = list(_convert_checks(checks, self.pvars))

    def run(self, df, on_error="remove"):
        if on_error not in [None, "remove", "replace"]:
            raise ValueError

        corrections, solutions = [], []
        for index, row in df.iterrows():
            corr, sol = self._run_row(row)
            corrections.append(corr)
            solutions.append(sol)
        corrections_df = pd.DataFrame(corrections)

        match on_error:
            case None:
                pass
            case "remove":
                for col, values in corrections_df.items():
                    df.loc[~values.isna(), col] = pd.NA
            case "replace":
                for col, values in corrections_df.items():
                    df.loc[~values.isna(), col] = values
            case _:
                raise Exception("Programming error: Forgot input validation?")

        return Result(corrections_df, solutions)  # Maybe return some kind of summary object in the future that summarizes errors.

    def _run_row(self, row):
        """Return a "corrected" row.

        To see where the errors occurred, check the keys. To replace, check the values.
        """
        model = self._setup_row(row)
        solution = model.solve()
        model_outcome = {var.name: var.value() for var in model.variables()}
        model_errors = {k.removesuffix(ERROR_SUFFIX): v >= 0.5 for k, v in model_outcome.items() if k.endswith("_error")}
        correction = {n: model_outcome[n] for n, err in model_errors.items() if err}
        return correction, solution

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

            # If a value exists, try to fix its value
            if value == value:
                errorvar = LpVariable(name=varname + "_error", lowBound=0, upBound=1, cat=LpInteger)
                target.append(errorvar * (1 + random() / 2))

                constraints += [(var <= value + errorvar * BIG, varname + "_ub"),
                                (var >= value - errorvar * BIG, varname + "_lb")]
        return lpSum(target), constraints


def _convert_checks(checks: Iterable[Check], pvars):
    converted_checks = []
    for check in checks:
        try:
            expression = check.get_expression()
            constraints = rewrite_condition(expression, pvars)
        except (TypeError, AttributeError):
            print(f"Unable to convert {check}")
            import traceback
            traceback.print_exc()
        else:
            print("Successfully converted: ", check)
            for i, constraint in enumerate(constraints):
                converted_checks.append((constraint, check.name + f"_{i}"))
    return converted_checks


class Result:
    def __init__(self, corrections_df, solutions):
        self.corrections_df = corrections_df
        self.solutions = solutions

    def get_errors(self):
        # Every cell that is True was an error, False has remained the same
        return ~self.corrections_df.isna()
