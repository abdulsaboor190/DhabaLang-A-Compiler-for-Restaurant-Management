import re

class Token:
    def __init__(self, type_: str, value: str, line: int, column: int):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, line={self.line}, col={self.column})"

KEYWORDS = {
    'MENU', 'DISH', 'INGREDIENT', 'ORDER', 'COMBO', 'SEASON', 
    'PRICE', 'NEEDS', 'APPLY_COMBO', 'PREP_TIME', 'END', 'DISCOUNT', 'INCLUDES'
}
SEASONS = {'all_year', 'winter', 'summer', 'monsoon'}
UNITS = {'kg', 'ml', 'L', 'piece', 'min', 'g'}

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self._tokenize()

    def _tokenize(self):
        token_specification = [
            ('COMMENT',   r'//[^\r\n]*'),
            ('DATE',      r'\d{4}-\d{2}-\d{2}'),
            ('FLOAT',     r'\d+\.\d+'),
            ('INTEGER',   r'\d+'),
            ('STRING',    r'"[^"]*"'),
            ('ID',        r'[A-Za-z_][A-Za-z0-9_]*'),
            ('OP',        r'[:%,]'),
            ('WS',        r'[ \t]+'),
            ('NEWLINE',   r'\r?\n'),
            ('UNKNOWN',   r'.'),
        ]
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
        
        for mo in re.finditer(tok_regex, self.text):
            kind = mo.lastgroup
            value = mo.group()
            col = self.column
            
            if kind == 'NEWLINE':
                self.line += 1
                self.column = 1
                continue
            elif kind in ('WS', 'COMMENT'):
                self.column += len(value)
                continue
            
            if kind == 'ID':
                if value in KEYWORDS:
                    kind = 'KEYWORD'
                elif value in SEASONS:
                    kind = 'SEASON'
                elif value in UNITS:
                    kind = 'UNIT'
                elif value == 'x':
                    kind = 'OP'
            elif kind == 'STRING':
                value = value[1:-1]
                
            elif kind == 'UNKNOWN':
                raise Exception(f"SyntaxError [Line {self.line}, Col {col}]: Unknown character '{value}'")
                
            self.tokens.append(Token(kind, value, self.line, col))
            self.column += len(mo.group())
