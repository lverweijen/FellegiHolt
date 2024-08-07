import ast
from collections import defaultdict

import pulp
from uneval import quote as q, to_ast

# These numbers are hard to chose and should perhaps be determined based on input
BIG = 1e6
SMALL = 0.5


class LpDict(defaultdict):
    def __missing__(self, key):
        v = pulp.LpVariable(key)
        self[key] = v
        return v


def rewrite_condition(node, pvars):
    """Convert uneval.Expression to iterable of pulp.Constraint"""
    node = to_ast(node)
    if isinstance(node, ast.Expression):
        node = node.body
    return _rewrite_condition(node, pvars)


def _rewrite_condition(node, pvars, slackvar=0):
    match node:
        case ast.Name(nid):
            var = pvars[nid]
            var.cat = 'Binary'
            yield var + slackvar >= 1
        case ast.UnaryOp(ast.Invert()):
            # It's quite difficult to negate an expression and this often fails
            for condition in _rewrite_condition(node.operand, pvars, -slackvar):
                if condition.sense != 0:
                    condition.sense *= -1
                    yield condition - condition.sense * SMALL
                else:
                    for sense in [-1, 1]:
                        c = condition.copy()
                        c.sense = sense
                        yield c - c.sense * SMALL
        case ast.BinOp(op=ast.BitOr()):
            subslackvar = pulp.LpVariable("_" + hex(id(node))[2:], cat="Binary")
            yield from _rewrite_condition(node.left, pvars, slackvar=slackvar + subslackvar)
            yield from _rewrite_condition(node.right, pvars, slackvar=slackvar + 1 - subslackvar)
        case ast.BinOp(op=ast.BitAnd()):
            yield from _rewrite_condition(node.left, pvars, slackvar=slackvar)
            yield from _rewrite_condition(node.right, pvars, slackvar=slackvar)
        case ast.Compare():
            condition = eval(ast.unparse(node), pvars)

            match node.ops:
                case [ast.GtE()]:
                    yield condition + BIG * slackvar
                case [ast.LtE()]:
                    yield condition - BIG * slackvar
                case [ast.Eq()]:
                    if slackvar == 0 and isinstance(slackvar, int):
                        # Because pulp tends to make LpVariable equal to 0
                        yield condition
                    else:
                        for sense in [-1, 1]:
                            c = condition.copy()
                            c.sense = sense
                            yield c + BIG * slackvar * c.sense
                case [op]:
                    raise TypeError(f"Comparison with {op} not yet supported.")
                case [_op1, _op2, *_ops]:
                    raise ValueError("Multiple compare not supported")
        case _:
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
    # parsed = ast.parse("x <= 5 or (food and x >= 10)", mode="eval").body
    # print(rewrite_condition(parsed))

    # expr = (q.age >= 18) | (q.married <= 0)
    # expr = (q.age >= 18) | (q.married <= 0) & (q.rare_exception)
    # expr = ~(q.married >= 1) | (q.age >= 18)
    # expr = ~(q.married >= 1) | ~(q.age == 18)
    # expr = ~(q.a == 5)
    expr = q.profit == q.turnover - q.cost
    print(list(rewrite_condition(expr, LpDict())))

main()
