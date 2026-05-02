"""
AST Printer — prints a formatted tree of the AST.
"""

from .ast_nodes import *


class ASTPrinter:
    def __init__(self):
        self.lines = []

    def print(self, node: ASTNode, prefix="", is_last=True) -> str:
        self.lines = []
        self._visit(node, "", True)
        return "\n".join(self.lines)

    def _connector(self, is_last: bool) -> str:
        return "└── " if is_last else "├── "

    def _child_prefix(self, prefix: str, is_last: bool) -> str:
        return prefix + ("    " if is_last else "│   ")

    def _visit(self, node, prefix, is_last):
        conn = self._connector(is_last)

        if isinstance(node, Program):
            self.lines.append(f"{prefix}{conn}Program")
            cp = self._child_prefix(prefix, is_last)
            for i, d in enumerate(node.declarations):
                self._visit(d, cp, i == len(node.declarations) - 1)

        elif isinstance(node, FunctionDef):
            self.lines.append(f"{prefix}{conn}FunctionDef: {node.return_type.name} {node.name}()")
            cp = self._child_prefix(prefix, is_last)
            for i, p in enumerate(node.params):
                self.lines.append(f"{cp}├── Param: {p.type_node.name} {p.name}")
            self._visit(node.body, cp, True)

        elif isinstance(node, Block):
            self.lines.append(f"{prefix}{conn}Block")
            cp = self._child_prefix(prefix, is_last)
            for i, s in enumerate(node.statements):
                self._visit(s, cp, i == len(node.statements) - 1)

        elif isinstance(node, VarDeclaration):
            self.lines.append(f"{prefix}{conn}VarDecl: {node.type_node.name} {node.name}")
            if node.initializer:
                cp = self._child_prefix(prefix, is_last)
                self._visit(node.initializer, cp, True)

        elif isinstance(node, IfStatement):
            self.lines.append(f"{prefix}{conn}If")
            cp = self._child_prefix(prefix, is_last)
            self._visit(node.condition, cp, False)
            self._visit(node.then_block, cp, node.else_block is None)
            if node.else_block:
                self._visit(node.else_block, cp, True)

        elif isinstance(node, WhileStatement):
            self.lines.append(f"{prefix}{conn}While")
            cp = self._child_prefix(prefix, is_last)
            self._visit(node.condition, cp, False)
            self._visit(node.body, cp, True)

        elif isinstance(node, ForStatement):
            self.lines.append(f"{prefix}{conn}For")
            cp = self._child_prefix(prefix, is_last)
            if node.init: self._visit(node.init, cp, False)
            if node.condition: self._visit(node.condition, cp, False)
            if node.update: self._visit(node.update, cp, False)
            self._visit(node.body, cp, True)

        elif isinstance(node, ReturnStatement):
            self.lines.append(f"{prefix}{conn}Return")
            if node.value:
                cp = self._child_prefix(prefix, is_last)
                self._visit(node.value, cp, True)

        elif isinstance(node, BinaryOp):
            self.lines.append(f"{prefix}{conn}BinaryOp: {node.op}")
            cp = self._child_prefix(prefix, is_last)
            self._visit(node.left, cp, False)
            self._visit(node.right, cp, True)

        elif isinstance(node, UnaryOp):
            pos = "prefix" if node.prefix else "postfix"
            self.lines.append(f"{prefix}{conn}UnaryOp: {node.op} ({pos})")
            cp = self._child_prefix(prefix, is_last)
            self._visit(node.operand, cp, True)

        elif isinstance(node, Assignment):
            self.lines.append(f"{prefix}{conn}Assignment: {node.op}")
            cp = self._child_prefix(prefix, is_last)
            self._visit(node.target, cp, False)
            self._visit(node.value, cp, True)

        elif isinstance(node, FunctionCall):
            self.lines.append(f"{prefix}{conn}FunctionCall: {node.name}()")
            cp = self._child_prefix(prefix, is_last)
            for i, a in enumerate(node.args):
                self._visit(a, cp, i == len(node.args) - 1)

        elif isinstance(node, PrintfCall):
            self.lines.append(f"{prefix}{conn}Printf: \"{node.format_str[:30]}\"")
            cp = self._child_prefix(prefix, is_last)
            for i, a in enumerate(node.args):
                self._visit(a, cp, i == len(node.args) - 1)

        elif isinstance(node, ArrayIndex):
            self.lines.append(f"{prefix}{conn}ArrayIndex")
            cp = self._child_prefix(prefix, is_last)
            self._visit(node.array, cp, False)
            self._visit(node.index, cp, True)

        elif isinstance(node, ExprStatement):
            self._visit(node.expr, prefix, is_last)

        elif isinstance(node, Identifier):
            self.lines.append(f"{prefix}{conn}Identifier: {node.name}")

        elif isinstance(node, IntLiteral):
            self.lines.append(f"{prefix}{conn}Int: {node.value}")

        elif isinstance(node, FloatLiteral):
            self.lines.append(f"{prefix}{conn}Float: {node.value}")

        elif isinstance(node, CharLiteral):
            self.lines.append(f"{prefix}{conn}Char: '{node.value}'")

        elif isinstance(node, StringLiteral):
            self.lines.append(f"{prefix}{conn}String: \"{node.value[:30]}\"")

        elif isinstance(node, BreakStatement):
            self.lines.append(f"{prefix}{conn}Break")

        elif isinstance(node, ContinueStatement):
            self.lines.append(f"{prefix}{conn}Continue")

        elif isinstance(node, DoWhileStatement):
            self.lines.append(f"{prefix}{conn}DoWhile")
            cp = self._child_prefix(prefix, is_last)
            self._visit(node.body, cp, False)
            self._visit(node.condition, cp, True)

        else:
            self.lines.append(f"{prefix}{conn}{type(node).__name__}")