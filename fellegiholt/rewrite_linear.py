import ast
from collections import defaultdict

import pulp
from uneval import quote as q, to_ast

BIG = 1e6
SMALL = 1e-6


class LpDict(defaultdict):
    def __missing__(self, key):
        v = pulp.LpVariable(key)
        self[key] = v
        return v


def rewrite_condition(node, pvars):
    # pvars = LpDict()
    node = to_ast(node)
    if isinstance(node, ast.Expression):
        node = node.body
    return _rewrite_condition(node, pvars)


def _rewrite_condition(node, pvars, slackvar=0):
    if isinstance(node, ast.Name):
        # var = pulp.LpVariable(name=node.id, cat='Binary')
        var = pvars[node.id]
        var.cat = 'Binary'
        yield var + slackvar >= 1
    elif isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Invert):
            for condition in _rewrite_condition(node.operand, pvars, -slackvar):
                if condition.sense != 0:
                    condition.sense *= -1
                    yield condition - condition.sense * SMALL
                else:
                    for sense in [-1, 1]:
                        c = condition.copy()
                        c.sense = sense
                        yield c - c.sense * SMALL
        else:
            raise TypeError(f"{node.op} is not supported.")
    elif isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.BitOr):
            subslackvar = pulp.LpVariable("_" + hex(id(node))[2:], cat="Binary")
            yield from _rewrite_condition(node.left, pvars, slackvar=slackvar + subslackvar)
            yield from _rewrite_condition(node.right, pvars, slackvar=slackvar + 1 - subslackvar)
        elif isinstance(node.op, ast.BitAnd):
            yield from _rewrite_condition(node.left, pvars, slackvar=slackvar)
            yield from _rewrite_condition(node.right, pvars, slackvar=slackvar)
        else:
            raise TypeError(f"{node.op} is not supported.")
    elif isinstance(node, ast.Compare):
        if len(node.ops) > 1:
            raise ValueError("Multiple compare not supported")
        [op] = node.ops
        code = ast.unparse(node)
        condition = eval(code, pvars)

        if isinstance(op, ast.GtE):
            yield condition + BIG * slackvar
        elif isinstance(op, ast.LtE):
            yield condition - BIG * slackvar
        elif isinstance(op, ast.Eq):
            if slackvar == 0 and isinstance(slackvar, int):
                # Because pulp tends to make LpVariable equal to 0
                yield condition
            else:
                for sense in [-1, 1]:
                    c = condition.copy()
                    c.sense = sense
                    yield c + BIG * slackvar * c.sense
        else:
            raise TypeError(f"Comparison with {op} not yet supported.")
    else:
        raise TypeError(f"{type(node)} not supported")


def main():
    # parsed = ast.parse("x <= 5", mode="eval").body
    # print(rewrite_compare(parsed))
    #
    # parsed = ast.parse("x <= 5 or x >= 10", mode="eval").body
    # print(rewrite_binop(parsed))
    #
    # parsed = ast.parse("x <= 5 or x >= 10", mode="eval").body
    # print(rewrite_condition(parsed))
    #
    # parsed = ast.parse("x <= 5 or (eten and x >= 10)", mode="eval").body
    # print(rewrite_condition(parsed))

    # expr = (q.age >= 18) | (q.married <= 0)
    # expr = (q.age >= 18) | (q.married <= 0) & (q.rare_exception)
    # expr = ~(q.married >= 1) | (q.age >= 18)
    # expr = ~(q.married >= 1) | ~(q.age == 18)
    expr = ~(q.a == 5)
    print(list(rewrite_condition(expr, LpDict())))

# main()
