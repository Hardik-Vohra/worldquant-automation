import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

TOKEN_RE = re.compile(r"\s*(?:(\d+\.\d+|\d+)|([A-Za-z_][A-Za-z0-9_]*)|(<=|>=|==|!=|[<>+\-*/(),]))")
COMPARISON_OPERATORS = {"<", ">", "<=", ">=", "==", "!="}
COMMUTATIVE_OPERATORS = {"+", "*"}


@dataclass
class AlphaNode:
    kind: str
    value: str
    children: List["AlphaNode"]

    def __str__(self):
        if self.kind == "function":
            args = ",".join(str(child) for child in self.children)
            return f"{self.value}({args})"

        if self.kind == "binary":
            return f"({str(self.children[0])}{self.value}{str(self.children[1])})"

        if self.kind == "unary":
            return f"({self.value}{str(self.children[0])})"

        return self.value

    def canonical(self):
        if self.kind == "function":
            args = [child.canonical() for child in self.children]
            return f"{self.value}({','.join(args)})"

        if self.kind == "binary":
            left = self.children[0].canonical()
            right = self.children[1].canonical()
            if self.value in COMMUTATIVE_OPERATORS:
                ordered = sorted([left, right])
                return f"({ordered[0]}{self.value}{ordered[1]})"
            return f"({left}{self.value}{right})"

        if self.kind == "unary":
            return f"({self.value}{self.children[0].canonical()})"

        return self.value

    def structure_signature(self):
        if self.kind == "function":
            args = [child.structure_signature() for child in self.children]
            return f"{self.value}({','.join(args)})"

        if self.kind == "binary":
            left = self.children[0].structure_signature()
            right = self.children[1].structure_signature()
            if self.value in COMMUTATIVE_OPERATORS:
                ordered = sorted([left, right])
                return f"({ordered[0]}{self.value}{ordered[1]})"
            return f"({left}{self.value}{right})"

        if self.kind == "unary":
            return f"({self.value}{self.children[0].structure_signature()})"

        if self.kind == "identifier":
            return "FIELD"

        if self.kind == "number":
            return "NUMBER"

        return self.value

    def operators(self):
        ops = set()
        if self.kind == "function":
            ops.add(self.value)
            for child in self.children:
                ops.update(child.operators())
        elif self.kind in {"binary", "unary"}:
            ops.add(self.value)
            for child in self.children:
                ops.update(child.operators())
        return ops

    def fields(self):
        fields = set()
        if self.kind == "function":
            for child in self.children:
                fields.update(child.fields())
        elif self.kind == "binary" or self.kind == "unary":
            for child in self.children:
                fields.update(child.fields())
        elif self.kind == "identifier":
            fields.add(self.value)
        return fields


class AlphaExpression:
    def __init__(self, expression: str):
        self.original = expression.strip()
        self.tokens = self._tokenize(self.original)
        self.position = 0
        self.root = self._parse_expression()

    @staticmethod
    def _tokenize(expression: str):
        tokens = []
        for number, name, symbol in TOKEN_RE.findall(expression):
            tokens.append(number or name or symbol)
        return tokens

    def _peek(self) -> Optional[str]:
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def _consume(self) -> Optional[str]:
        token = self._peek()
        self.position += 1
        return token

    def _parse_expression(self):
        node = self._parse_comparison()
        while self._peek() in {"+", "-"}:
            op = self._consume()
            right = self._parse_comparison()
            node = AlphaNode(kind="binary", value=op, children=[node, right])
        return node

    def _parse_comparison(self):
        node = self._parse_term()
        while self._peek() in {"<", ">", "<=", ">=", "==", "!="}:
            op = self._consume()
            right = self._parse_term()
            node = AlphaNode(kind="binary", value=op, children=[node, right])
        return node

    def _parse_term(self):
        node = self._parse_factor()
        while self._peek() in {"*", "/"}:
            op = self._consume()
            right = self._parse_factor()
            node = AlphaNode(kind="binary", value=op, children=[node, right])
        return node

    def _parse_factor(self):
        token = self._peek()
        if token == "-":
            self._consume()
            child = self._parse_factor()
            return AlphaNode(kind="unary", value="-", children=[child])

        if token == "(":
            self._consume()
            node = self._parse_expression()
            if self._peek() == ")":
                self._consume()
            return node

        if token and re.match(r"^\d+(?:\.\d+)?$", token):
            self._consume()
            return AlphaNode(kind="number", value=token, children=[])

        if token and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", token):
            name = self._consume()
            if self._peek() == "(":
                self._consume()
                args = []
                if self._peek() != ")":
                    while True:
                        args.append(self._parse_expression())
                        if self._peek() == ",":
                            self._consume()
                            continue
                        break
                if self._peek() == ")":
                    self._consume()
                return AlphaNode(kind="function", value=name, children=args)
            return AlphaNode(kind="identifier", value=name, children=[])

        raise ValueError(f"Unable to parse token: {token}")

    def canonical(self) -> str:
        return self.root.canonical() if self.root else ""

    def signature(self) -> str:
        return self.canonical()

    def structure_signature(self) -> str:
        return self.root.structure_signature() if self.root else ""

    def operator_set(self):
        return self.root.operators() if self.root else set()

    def field_set(self):
        return self.root.fields() if self.root else set()

    def similarity(self, other: "AlphaExpression") -> float:
        a = self.field_set()
        b = other.field_set()
        oa = self.operator_set()
        ob = other.operator_set()
        field_sim = 0.0
        if a or b:
            field_sim = len(a & b) / len(a | b)
        op_sim = 0.0
        if oa or ob:
            op_sim = len(oa & ob) / len(oa | ob)
        return 0.6 * field_sim + 0.4 * op_sim

    def is_similar(self, other: "AlphaExpression", threshold: float = 0.8) -> bool:
        if self.signature() == other.signature():
            return True
        if self.structure_signature() == other.structure_signature():
            return True
        return self.similarity(other) >= threshold


if __name__ == "__main__":
    expr = AlphaExpression("trade_when(pcr_oi_270<1,ts_delta(anl4_ebit_value,126),-1)")
    print(expr)
    print(expr.canonical())
    print(expr.field_set())
    print(expr.operator_set())
