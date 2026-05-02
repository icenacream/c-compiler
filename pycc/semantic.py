"""
Semantic Analyzer.
- Builds symbol tables (scoped)
- Type checking
- Detects undeclared variables, redeclarations, wrong return types, etc.
"""

from typing import Dict, List, Optional, Tuple
from .ast_nodes import *


class SemanticError(Exception):
    def __init__(self, message: str):
        super().__init__(f"Semantic Error: {message}")



#  Symbol table 
class Symbol:
    def __init__(self, name: str, type_node: TypeNode, kind: str = 'var'):
        self.name = name
        self.type_node = type_node
        self.kind = kind  # 'var', 'param', 'func'


class Scope:
    def __init__(self, parent: Optional['Scope'] = None):
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, sym: Symbol):
        if sym.name in self.symbols:
            raise SemanticError(f"Redeclaration of '{sym.name}'")
        self.symbols[sym.name] = sym

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)


#  Analyzer 
class SemanticAnalyzer:
    def __init__(self):
        self.global_scope = Scope()
        self.current_scope = self.global_scope
        self.current_function: Optional[FunctionDef] = None
        self.loop_depth = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, msg: str):
        self.errors.append(f"Semantic Error: {msg}")

    def warn(self, msg: str):
        self.warnings.append(f"Warning: {msg}")

    def enter_scope(self):
        self.current_scope = Scope(parent=self.current_scope)

    def exit_scope(self):
        self.current_scope = self.current_scope.parent

    #  Entry point 

    def analyze(self, program: Program):
        for decl in program.declarations:
            self.visit(decl)
        # Check for main
        main_sym = self.global_scope.lookup('main')
        if main_sym is None or main_sym.kind != 'func':
            self.warn("No 'main' function found")
        return len(self.errors) == 0

    def visit(self, node: ASTNode):
        method = f"visit_{type(node).__name__}"
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode):
        pass

    #  Declarations 

    def visit_Program(self, node: Program):
        for decl in node.declarations:
            self.visit(decl)

    def visit_FunctionDef(self, node: FunctionDef):
        # Register function in current (global) scope
        func_type = TypeNode(name=node.return_type.name)
        sym = Symbol(node.name, func_type, kind='func')
        try:
            self.current_scope.define(sym)
        except SemanticError as e:
            self.error(str(e))

        prev_func = self.current_function
        self.current_function = node
        self.enter_scope()

        # Register parameters
        for param in node.params:
            psym = Symbol(param.name, param.type_node, kind='param')
            try:
                self.current_scope.define(psym)
            except SemanticError as e:
                self.error(str(e))

        self.visit(node.body)
        self.exit_scope()
        self.current_function = prev_func

    def visit_VarDeclaration(self, node: VarDeclaration):
        sym = Symbol(node.name, node.type_node, kind='var')
        try:
            self.current_scope.define(sym)
        except SemanticError as e:
            self.error(str(e))
        if node.initializer:
            self.visit(node.initializer)

    #  Statements 

    def visit_Block(self, node: Block):
        self.enter_scope()
        for stmt in node.statements:
            self.visit(stmt)
        self.exit_scope()

    def visit_IfStatement(self, node: IfStatement):
        self.visit(node.condition)
        self.visit(node.then_block)
        if node.else_block:
            self.visit(node.else_block)

    def visit_WhileStatement(self, node: WhileStatement):
        self.visit(node.condition)
        self.loop_depth += 1
        self.visit(node.body)
        self.loop_depth -= 1

    def visit_DoWhileStatement(self, node: DoWhileStatement):
        self.loop_depth += 1
        self.visit(node.body)
        self.loop_depth -= 1
        self.visit(node.condition)

    def visit_ForStatement(self, node: ForStatement):
        self.enter_scope()
        if node.init:
            self.visit(node.init)
        if node.condition:
            self.visit(node.condition)
        if node.update:
            self.visit(node.update)
        self.loop_depth += 1
        self.visit(node.body)
        self.loop_depth -= 1
        self.exit_scope()

    def visit_ReturnStatement(self, node: ReturnStatement):
        if self.current_function is None:
            self.error("'return' outside function")
        if node.value:
            self.visit(node.value)
            if self.current_function and self.current_function.return_type.name == 'void':
                self.warn(f"Returning value from void function '{self.current_function.name}'")
        elif self.current_function and self.current_function.return_type.name != 'void':
            self.warn(f"Missing return value in non-void function '{self.current_function.name}'")

    def visit_BreakStatement(self, node: BreakStatement):
        if self.loop_depth == 0:
            self.error("'break' outside loop")

    def visit_ContinueStatement(self, node: ContinueStatement):
        if self.loop_depth == 0:
            self.error("'continue' outside loop")

    def visit_ExprStatement(self, node: ExprStatement):
        self.visit(node.expr)

    #  Expressions 

    def visit_Identifier(self, node: Identifier):
        sym = self.current_scope.lookup(node.name)
        if sym is None:
            self.error(f"Undeclared identifier '{node.name}'")

    def visit_BinaryOp(self, node: BinaryOp):
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node: UnaryOp):
        self.visit(node.operand)

    def visit_Assignment(self, node: Assignment):
        self.visit(node.target)
        self.visit(node.value)
        if isinstance(node.target, Identifier):
            sym = self.current_scope.lookup(node.target.name)
            if sym and sym.type_node.name == 'void':
                self.error(f"Cannot assign to void type")

    def visit_FunctionCall(self, node: FunctionCall):
        sym = self.current_scope.lookup(node.name)
        if sym is None:
            self.error(f"Undeclared function '{node.name}'")
        elif sym.kind != 'func':
            self.error(f"'{node.name}' is not a function")
        for arg in node.args:
            self.visit(arg)

    def visit_ArrayIndex(self, node: ArrayIndex):
        self.visit(node.array)
        self.visit(node.index)

    def visit_PrintfCall(self, node: PrintfCall):
        for arg in node.args:
            self.visit(arg)

    # literals — nothing to check
    def visit_IntLiteral(self, node): pass
    def visit_FloatLiteral(self, node): pass
    def visit_CharLiteral(self, node): pass
    def visit_StringLiteral(self, node): pass