"""
Recursive-Descent Parser for C language.
Consumes tokens from the Lexer and builds an AST.

Grammar (simplified):
  program         → declaration*
  declaration     → func_def | var_decl
  func_def        → type IDENT '(' params ')' block
  var_decl        → type IDENT ( '=' expr )? ';'
  block           → '{' statement* '}'
  statement       → var_decl | if_stmt | while_stmt | for_stmt |
                    do_while_stmt | return_stmt | break_stmt |
                    continue_stmt | expr_stmt | block
  expr_stmt       → expr ';'
  expr            → assignment
  assignment      → logical ( ('='|'+='|'-='|'*='|'/=') assignment )?
  logical         → equality ( ('&&'|'||') equality )*
  equality        → relational ( ('=='|'!=') relational )*
  relational      → additive ( ('<'|'<='|'>'|'>=') additive )*
  additive        → multiplicative ( ('+'|'-') multiplicative )*
  multiplicative  → unary ( ('*'|'/'|'%') unary )*
  unary           → ('!'|'-'|'++'|'--') unary | postfix
  postfix         → primary ( '++'|'--'|'[' expr ']'|'(' args ')' )*
  primary         → INT_LITERAL | FLOAT_LITERAL | CHAR_LITERAL |
                    STRING_LITERAL | IDENT | '(' expr ')' | printf_call
"""

from typing import List, Optional
from .lexer import Token, TokenType
from .ast_nodes import *


class ParseError(Exception):
    def __init__(self, message, token: Token):
        super().__init__(f"Parse Error at line {token.line}, col {token.col}: {message} (got {token.type.name} {token.value!r})")
        self.token = token


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    #  Helpers 

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def peek_type(self) -> TokenType:
        return self.tokens[self.pos].type

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def check(self, *types: TokenType) -> bool:
        return self.peek_type() in types

    def match(self, *types: TokenType) -> Optional[Token]:
        if self.peek_type() in types:
            return self.advance()
        return None

    def expect(self, typ: TokenType, msg: str = None) -> Token:
        if self.peek_type() == typ:
            return self.advance()
        raise ParseError(msg or f"Expected {typ.name}", self.peek())

    def error(self, msg: str):
        raise ParseError(msg, self.peek())

    def is_type_keyword(self) -> bool:
        return self.check(TokenType.INT, TokenType.FLOAT, TokenType.CHAR, TokenType.VOID)

    #  Type parsing 

    def parse_type(self) -> TypeNode:
        type_map = {
            TokenType.INT: 'int', TokenType.FLOAT: 'float',
            TokenType.CHAR: 'char', TokenType.VOID: 'void',
        }
        tok = self.advance()
        name = type_map.get(tok.type)
        if name is None:
            raise ParseError("Expected type keyword", tok)
        pointer = bool(self.match(TokenType.STAR))
        return TypeNode(name=name, pointer=pointer)

    #  Top-level 

    def parse(self) -> Program:
        decls = []
        while not self.check(TokenType.EOF):
            decls.append(self.parse_global())
        return Program(declarations=decls)

    def parse_global(self) -> ASTNode:
        """Parse a top-level function or global variable declaration."""
        type_node = self.parse_type()
        name = self.expect(TokenType.IDENTIFIER, "Expected identifier").value

        if self.check(TokenType.LPAREN):
            # Function definition
            return self.parse_func_def(type_node, name)
        else:
            # Global variable
            init = None
            if self.match(TokenType.EQ):
                init = self.parse_expr()
            self.expect(TokenType.SEMICOLON, "Expected ';' after variable declaration")
            return VarDeclaration(type_node=type_node, name=name, initializer=init)

    def parse_func_def(self, return_type: TypeNode, name: str) -> FunctionDef:
        self.expect(TokenType.LPAREN, "Expected '(' after function name")
        params = []
        if not self.check(TokenType.RPAREN):
            params = self.parse_params()
        self.expect(TokenType.RPAREN, "Expected ')' after parameters")
        body = self.parse_block()
        return FunctionDef(return_type=return_type, name=name, params=params, body=body)

    def parse_params(self) -> List[FunctionParam]:
        params = []
        while True:
            if self.check(TokenType.VOID) and self.tokens[self.pos+1].type == TokenType.RPAREN:
                self.advance()  # consume void
                break
            t = self.parse_type()
            n = self.expect(TokenType.IDENTIFIER, "Expected parameter name").value
            params.append(FunctionParam(type_node=t, name=n))
            if not self.match(TokenType.COMMA):
                break
        return params

    #  Statements 

    def parse_block(self) -> Block:
        self.expect(TokenType.LBRACE, "Expected '{'")
        stmts = []
        while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
            stmts.append(self.parse_statement())
        self.expect(TokenType.RBRACE, "Expected '}'")
        return Block(statements=stmts)

    def parse_statement(self) -> ASTNode:
        tt = self.peek_type()

        if tt == TokenType.LBRACE:
            return self.parse_block()
        elif tt == TokenType.IF:
            return self.parse_if()
        elif tt == TokenType.WHILE:
            return self.parse_while()
        elif tt == TokenType.DO:
            return self.parse_do_while()
        elif tt == TokenType.FOR:
            return self.parse_for()
        elif tt == TokenType.RETURN:
            return self.parse_return()
        elif tt == TokenType.BREAK:
            self.advance()
            self.expect(TokenType.SEMICOLON)
            return BreakStatement()
        elif tt == TokenType.CONTINUE:
            self.advance()
            self.expect(TokenType.SEMICOLON)
            return ContinueStatement()
        elif self.is_type_keyword():
            return self.parse_var_decl()
        else:
            return self.parse_expr_stmt()

    def parse_var_decl(self) -> VarDeclaration:
        t = self.parse_type()
        name = self.expect(TokenType.IDENTIFIER, "Expected variable name").value
        # Handle array declaration: int arr[size]
        if self.match(TokenType.LBRACKET):
            size = None
            if not self.check(TokenType.RBRACKET):
                size_tok = self.expect(TokenType.INT_LITERAL, "Expected array size")
                size = int(size_tok.value)
                t = TypeNode(name=t.name, pointer=t.pointer, array_size=size)
            self.expect(TokenType.RBRACKET, "Expected ']'")
        init = None
        if self.match(TokenType.EQ):
            init = self.parse_expr()
        self.expect(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VarDeclaration(type_node=t, name=name, initializer=init)

    def parse_if(self) -> IfStatement:
        self.expect(TokenType.IF)
        self.expect(TokenType.LPAREN, "Expected '(' after 'if'")
        cond = self.parse_expr()
        self.expect(TokenType.RPAREN, "Expected ')' after if condition")
        then_block = self.parse_statement()
        else_block = None
        if self.match(TokenType.ELSE):
            else_block = self.parse_statement()
        return IfStatement(condition=cond, then_block=then_block, else_block=else_block)

    def parse_while(self) -> WhileStatement:
        self.expect(TokenType.WHILE)
        self.expect(TokenType.LPAREN, "Expected '(' after 'while'")
        cond = self.parse_expr()
        self.expect(TokenType.RPAREN, "Expected ')' after while condition")
        body = self.parse_statement()
        return WhileStatement(condition=cond, body=body)

    def parse_do_while(self) -> DoWhileStatement:
        self.expect(TokenType.DO)
        body = self.parse_statement()
        self.expect(TokenType.WHILE, "Expected 'while' after do body")
        self.expect(TokenType.LPAREN)
        cond = self.parse_expr()
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.SEMICOLON)
        return DoWhileStatement(body=body, condition=cond)

    def parse_for(self) -> ForStatement:
        self.expect(TokenType.FOR)
        self.expect(TokenType.LPAREN)
        # init
        if self.check(TokenType.SEMICOLON):
            init = None; self.advance()
        elif self.is_type_keyword():
            t = self.parse_type()
            nm = self.expect(TokenType.IDENTIFIER).value
            iv = None
            if self.match(TokenType.EQ): iv = self.parse_expr()
            self.expect(TokenType.SEMICOLON)
            init = VarDeclaration(type_node=t, name=nm, initializer=iv)
        else:
            init = self.parse_expr()
            self.expect(TokenType.SEMICOLON)
        # condition
        cond = None
        if not self.check(TokenType.SEMICOLON):
            cond = self.parse_expr()
        self.expect(TokenType.SEMICOLON)
        # update
        update = None
        if not self.check(TokenType.RPAREN):
            update = self.parse_expr()
        self.expect(TokenType.RPAREN)
        body = self.parse_statement()
        return ForStatement(init=init, condition=cond, update=update, body=body)

    def parse_return(self) -> ReturnStatement:
        self.expect(TokenType.RETURN)
        val = None
        if not self.check(TokenType.SEMICOLON):
            val = self.parse_expr()
        self.expect(TokenType.SEMICOLON)
        return ReturnStatement(value=val)

    def parse_expr_stmt(self) -> ExprStatement:
        expr = self.parse_expr()
        self.expect(TokenType.SEMICOLON, "Expected ';' after expression")
        return ExprStatement(expr=expr)

    #  Expressions (Pratt / recursive-descent) 

    def parse_expr(self) -> ASTNode:
        return self.parse_assignment()

    def parse_assignment(self) -> ASTNode:
        left = self.parse_logical_or()
        op = self.match(TokenType.EQ, TokenType.PLUSEQ, TokenType.MINUSEQ,
                        TokenType.STAREQ, TokenType.SLASHEQ)
        if op:
            right = self.parse_assignment()
            return Assignment(op=op.value, target=left, value=right)
        return left

    def parse_logical_or(self) -> ASTNode:
        node = self.parse_logical_and()
        while (op := self.match(TokenType.OR)):
            node = BinaryOp(op='||', left=node, right=self.parse_logical_and())
        return node

    def parse_logical_and(self) -> ASTNode:
        node = self.parse_equality()
        while (op := self.match(TokenType.AND)):
            node = BinaryOp(op='&&', left=node, right=self.parse_equality())
        return node

    def parse_equality(self) -> ASTNode:
        node = self.parse_relational()
        while (op := self.match(TokenType.EQEQ, TokenType.NEQ)):
            node = BinaryOp(op=op.value, left=node, right=self.parse_relational())
        return node

    def parse_relational(self) -> ASTNode:
        node = self.parse_additive()
        while (op := self.match(TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE)):
            node = BinaryOp(op=op.value, left=node, right=self.parse_additive())
        return node

    def parse_additive(self) -> ASTNode:
        node = self.parse_multiplicative()
        while (op := self.match(TokenType.PLUS, TokenType.MINUS)):
            node = BinaryOp(op=op.value, left=node, right=self.parse_multiplicative())
        return node

    def parse_multiplicative(self) -> ASTNode:
        node = self.parse_unary()
        while (op := self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT)):
            node = BinaryOp(op=op.value, left=node, right=self.parse_unary())
        return node

    def parse_unary(self) -> ASTNode:
        if (op := self.match(TokenType.MINUS)):
            return UnaryOp(op='-', operand=self.parse_unary(), prefix=True)
        if (op := self.match(TokenType.NOT)):
            return UnaryOp(op='!', operand=self.parse_unary(), prefix=True)
        if (op := self.match(TokenType.PLUSPLUS)):
            return UnaryOp(op='++', operand=self.parse_unary(), prefix=True)
        if (op := self.match(TokenType.MINUSMINUS)):
            return UnaryOp(op='--', operand=self.parse_unary(), prefix=True)
        return self.parse_postfix()

    def parse_postfix(self) -> ASTNode:
        node = self.parse_primary()
        while True:
            if self.match(TokenType.PLUSPLUS):
                node = UnaryOp(op='++', operand=node, prefix=False)
            elif self.match(TokenType.MINUSMINUS):
                node = UnaryOp(op='--', operand=node, prefix=False)
            elif self.match(TokenType.LBRACKET):
                idx = self.parse_expr()
                self.expect(TokenType.RBRACKET)
                node = ArrayIndex(array=node, index=idx)
            elif self.check(TokenType.LPAREN) and isinstance(node, Identifier):
                self.advance()
                args = []
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expr())
                    while self.match(TokenType.COMMA):
                        args.append(self.parse_expr())
                self.expect(TokenType.RPAREN)
                node = FunctionCall(name=node.name, args=args)
            else:
                break
        return node

    def parse_primary(self) -> ASTNode:
        tt = self.peek_type()
        tok = self.peek()

        if tt == TokenType.INT_LITERAL:
            self.advance()
            return IntLiteral(value=int(tok.value))
        elif tt == TokenType.FLOAT_LITERAL:
            self.advance()
            return FloatLiteral(value=float(tok.value))
        elif tt == TokenType.CHAR_LITERAL:
            self.advance()
            return CharLiteral(value=tok.value)
        elif tt == TokenType.STRING_LITERAL:
            self.advance()
            return StringLiteral(value=tok.value)
        elif tt == TokenType.IDENTIFIER:
            self.advance()
            return Identifier(name=tok.value)
        elif tt == TokenType.PRINTF:
            return self.parse_printf()
        elif tt == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(TokenType.RPAREN, "Expected ')' after grouped expression")
            return expr
        else:
            self.error(f"Unexpected token in expression: {tok.type.name} {tok.value!r}")

    def parse_printf(self) -> PrintfCall:
        self.expect(TokenType.PRINTF)
        self.expect(TokenType.LPAREN)
        fmt_tok = self.peek()
        if fmt_tok.type != TokenType.STRING_LITERAL:
            self.error("printf requires a string literal as first argument")
        self.advance()
        fmt = fmt_tok.value
        args = []
        while self.match(TokenType.COMMA):
            args.append(self.parse_expr())
        self.expect(TokenType.RPAREN)
        return PrintfCall(format_str=fmt, args=args)