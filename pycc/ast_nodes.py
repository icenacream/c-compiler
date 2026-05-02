"""
Abstract Syntax Tree (AST) node definitions.
Each class represents a syntactic construct in C.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any


#  Base 

class ASTNode:
    """Base class for all AST nodes."""
    pass


#  Types 

@dataclass
class TypeNode(ASTNode):
    name: str          # 'int', 'float', 'char', 'void'
    pointer: bool = False
    array_size: Optional[int] = None


#  Expressions 

@dataclass
class IntLiteral(ASTNode):
    value: int

@dataclass
class FloatLiteral(ASTNode):
    value: float

@dataclass
class CharLiteral(ASTNode):
    value: str

@dataclass
class StringLiteral(ASTNode):
    value: str

@dataclass
class Identifier(ASTNode):
    name: str

@dataclass
class BinaryOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode

@dataclass
class UnaryOp(ASTNode):
    op: str      # '-', '!', '++', '--', '&', '*'
    operand: ASTNode
    prefix: bool = True

@dataclass
class Assignment(ASTNode):
    op: str      # '=', '+=', '-=', '*=', '/='
    target: ASTNode
    value: ASTNode

@dataclass
class FunctionCall(ASTNode):
    name: str
    args: List[ASTNode]

@dataclass
class ArrayIndex(ASTNode):
    array: ASTNode
    index: ASTNode

@dataclass
class PrintfCall(ASTNode):
    format_str: str
    args: List[ASTNode]


#  Statements 

@dataclass
class ExprStatement(ASTNode):
    expr: ASTNode

@dataclass
class ReturnStatement(ASTNode):
    value: Optional[ASTNode]

@dataclass
class BreakStatement(ASTNode):
    pass

@dataclass
class ContinueStatement(ASTNode):
    pass

@dataclass
class Block(ASTNode):
    statements: List[ASTNode]

@dataclass
class VarDeclaration(ASTNode):
    type_node: TypeNode
    name: str
    initializer: Optional[ASTNode] = None

@dataclass
class IfStatement(ASTNode):
    condition: ASTNode
    then_block: ASTNode
    else_block: Optional[ASTNode] = None

@dataclass
class WhileStatement(ASTNode):
    condition: ASTNode
    body: ASTNode

@dataclass
class DoWhileStatement(ASTNode):
    body: ASTNode
    condition: ASTNode

@dataclass
class ForStatement(ASTNode):
    init: Optional[ASTNode]
    condition: Optional[ASTNode]
    update: Optional[ASTNode]
    body: ASTNode


#  Top-level

@dataclass
class FunctionParam(ASTNode):
    type_node: TypeNode
    name: str

@dataclass
class FunctionDef(ASTNode):
    return_type: TypeNode
    name: str
    params: List[FunctionParam]
    body: Block

@dataclass
class Program(ASTNode):
    declarations: List[ASTNode]   # FunctionDef or VarDeclaration (global)