"""
Tokenizer for C language.
Converts raw source code into a tokens.
"""

import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    # Literals
    INT_LITERAL    = auto()
    FLOAT_LITERAL  = auto()
    CHAR_LITERAL   = auto()
    STRING_LITERAL = auto()

    # Identifiers & Keywords
    IDENTIFIER = auto()
    # Keywords
    INT    = auto()
    FLOAT  = auto()
    CHAR   = auto()
    VOID   = auto()
    RETURN = auto()
    IF     = auto()
    ELSE   = auto()
    WHILE  = auto()
    FOR    = auto()
    DO     = auto()
    BREAK  = auto()
    CONTINUE = auto()
    PRINTF = auto()   # built-in treated as keyword for simplicity

    # Operators
    PLUS    = auto()  # +
    MINUS   = auto()  # -
    STAR    = auto()  # *
    SLASH   = auto()  # /
    PERCENT = auto()  # %
    EQ      = auto()  # =
    EQEQ    = auto()  # ==
    NEQ     = auto()  # !=
    LT      = auto()  # <
    LTE     = auto()  # <=
    GT      = auto()  # >
    GTE     = auto()  # >=
    AND     = auto()  # &&
    OR      = auto()  # ||
    NOT     = auto()  # !
    AMP     = auto()  # &
    PIPE    = auto()  # |
    PLUSEQ  = auto()  # +=
    MINUSEQ = auto()  # -=
    STAREQ  = auto()  # *=
    SLASHEQ = auto()  # /=
    PLUSPLUS   = auto()  # ++
    MINUSMINUS = auto()  # --

    # Delimiters
    LPAREN    = auto()  # (
    RPAREN    = auto()  # )
    LBRACE    = auto()  # {
    RBRACE    = auto()  # }
    LBRACKET  = auto()  # [
    RBRACKET  = auto()  # ]
    SEMICOLON = auto()  # ;
    COMMA     = auto()  # ,

    # Special
    EOF = auto()


KEYWORDS = {
    'int':      TokenType.INT,
    'float':    TokenType.FLOAT,
    'char':     TokenType.CHAR,
    'void':     TokenType.VOID,
    'return':   TokenType.RETURN,
    'if':       TokenType.IF,
    'else':     TokenType.ELSE,
    'while':    TokenType.WHILE,
    'for':      TokenType.FOR,
    'do':       TokenType.DO,
    'break':    TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'printf':   TokenType.PRINTF,
}


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.col})"


class LexerError(Exception):
    def __init__(self, message, line, col):
        super().__init__(f"Lexer Error at line {line}, col {col}: {message}")
        self.line = line
        self.col = col


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    def error(self, msg):
        raise LexerError(msg, self.line, self.col)

    def peek(self, offset=0) -> Optional[str]:
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return None

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.pos < len(self.source) and self.source[self.pos] == expected:
            self.advance()
            return True
        return False

    def skip_whitespace_and_comments(self):
        while self.pos < len(self.source):
            ch = self.peek()
            if ch in (' ', '\t', '\r', '\n'):
                self.advance()
            elif ch == '/' and self.peek(1) == '/':
                # Single-line comment
                while self.pos < len(self.source) and self.peek() != '\n':
                    self.advance()
            elif ch == '/' and self.peek(1) == '*':
                # Multi-line comment
                self.advance(); self.advance()
                while self.pos < len(self.source):
                    if self.peek() == '*' and self.peek(1) == '/':
                        self.advance(); self.advance()
                        break
                    self.advance()
            else:
                break

    def read_string(self) -> Token:
        line, col = self.line, self.col
        self.advance()  # consume opening "
        result = []
        while self.pos < len(self.source):
            ch = self.peek()
            if ch == '"':
                self.advance()
                break
            elif ch == '\\':
                self.advance()
                esc = self.advance()
                escapes = {'n': '\n', 't': '\t', '\\': '\\', '"': '"', '0': '\0', 'r': '\r'}
                result.append(escapes.get(esc, esc))
            elif ch == '\n':
                self.error("Unterminated string literal")
            else:
                result.append(self.advance())
        else:
            self.error("Unterminated string literal")
        return Token(TokenType.STRING_LITERAL, ''.join(result), line, col)

    def read_char(self) -> Token:
        line, col = self.line, self.col
        self.advance()  # consume opening '
        ch = self.advance()
        if ch == '\\':
            esc = self.advance()
            escapes = {'n': '\n', 't': '\t', '\\': '\\', "'": "'", '0': '\0'}
            ch = escapes.get(esc, esc)
        if not self.match("'"):
            self.error("Unterminated char literal")
        return Token(TokenType.CHAR_LITERAL, ch, line, col)

    def read_number(self) -> Token:
        line, col = self.line, self.col
        result = []
        is_float = False
        while self.pos < len(self.source) and (self.peek().isdigit() or self.peek() == '.'):
            ch = self.advance()
            if ch == '.':
                is_float = True
            result.append(ch)
        value = ''.join(result)
        typ = TokenType.FLOAT_LITERAL if is_float else TokenType.INT_LITERAL
        return Token(typ, value, line, col)

    def read_identifier(self) -> Token:
        line, col = self.line, self.col
        result = []
        while self.pos < len(self.source) and (self.peek().isalnum() or self.peek() == '_'):
            result.append(self.advance())
        value = ''.join(result)
        typ = KEYWORDS.get(value, TokenType.IDENTIFIER)
        return Token(typ, value, line, col)

    def tokenize(self) -> List[Token]:
        while True:
            self.skip_whitespace_and_comments()
            if self.pos >= len(self.source):
                self.tokens.append(Token(TokenType.EOF, '', self.line, self.col))
                break

            line, col = self.line, self.col
            ch = self.peek()

            # String & char literals
            if ch == '"':
                self.tokens.append(self.read_string())
            elif ch == "'":
                self.tokens.append(self.read_char())
            # Numbers
            elif ch.isdigit() or (ch == '.' and self.peek(1) and self.peek(1).isdigit()):
                self.tokens.append(self.read_number())
            # Identifiers / keywords
            elif ch.isalpha() or ch == '_':
                self.tokens.append(self.read_identifier())
            # Operators & delimiters
            else:
                self.advance()
                if ch == '+':
                    if self.match('+'):   self.tokens.append(Token(TokenType.PLUSPLUS, '++', line, col))
                    elif self.match('='): self.tokens.append(Token(TokenType.PLUSEQ, '+=', line, col))
                    else:                 self.tokens.append(Token(TokenType.PLUS, '+', line, col))
                elif ch == '-':
                    if self.match('-'):   self.tokens.append(Token(TokenType.MINUSMINUS, '--', line, col))
                    elif self.match('='): self.tokens.append(Token(TokenType.MINUSEQ, '-=', line, col))
                    else:                 self.tokens.append(Token(TokenType.MINUS, '-', line, col))
                elif ch == '*':
                    if self.match('='): self.tokens.append(Token(TokenType.STAREQ, '*=', line, col))
                    else:               self.tokens.append(Token(TokenType.STAR, '*', line, col))
                elif ch == '/':
                    if self.match('='): self.tokens.append(Token(TokenType.SLASHEQ, '/=', line, col))
                    else:               self.tokens.append(Token(TokenType.SLASH, '/', line, col))
                elif ch == '%':  self.tokens.append(Token(TokenType.PERCENT, '%', line, col))
                elif ch == '=':
                    if self.match('='): self.tokens.append(Token(TokenType.EQEQ, '==', line, col))
                    else:               self.tokens.append(Token(TokenType.EQ, '=', line, col))
                elif ch == '!':
                    if self.match('='): self.tokens.append(Token(TokenType.NEQ, '!=', line, col))
                    else:               self.tokens.append(Token(TokenType.NOT, '!', line, col))
                elif ch == '<':
                    if self.match('='): self.tokens.append(Token(TokenType.LTE, '<=', line, col))
                    else:               self.tokens.append(Token(TokenType.LT, '<', line, col))
                elif ch == '>':
                    if self.match('='): self.tokens.append(Token(TokenType.GTE, '>=', line, col))
                    else:               self.tokens.append(Token(TokenType.GT, '>', line, col))
                elif ch == '&':
                    if self.match('&'): self.tokens.append(Token(TokenType.AND, '&&', line, col))
                    else:               self.tokens.append(Token(TokenType.AMP, '&', line, col))
                elif ch == '|':
                    if self.match('|'): self.tokens.append(Token(TokenType.OR, '||', line, col))
                    else:               self.tokens.append(Token(TokenType.PIPE, '|', line, col))
                elif ch == '(':  self.tokens.append(Token(TokenType.LPAREN, '(', line, col))
                elif ch == ')':  self.tokens.append(Token(TokenType.RPAREN, ')', line, col))
                elif ch == '{':  self.tokens.append(Token(TokenType.LBRACE, '{', line, col))
                elif ch == '}':  self.tokens.append(Token(TokenType.RBRACE, '}', line, col))
                elif ch == '[':  self.tokens.append(Token(TokenType.LBRACKET, '[', line, col))
                elif ch == ']':  self.tokens.append(Token(TokenType.RBRACKET, ']', line, col))
                elif ch == ';':  self.tokens.append(Token(TokenType.SEMICOLON, ';', line, col))
                elif ch == ',':  self.tokens.append(Token(TokenType.COMMA, ',', line, col))
                else:
                    self.error(f"Unexpected character: {ch!r}")

        return self.tokens