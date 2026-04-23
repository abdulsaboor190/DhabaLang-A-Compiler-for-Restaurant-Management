from typing import List, Optional
from lexer import Token
from ast_nodes import *

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_type=None, expected_value=None) -> Token:
        tok = self.peek()
        if not tok:
            expected_str = expected_value if expected_value else expected_type
            raise Exception(f"SyntaxError: Expected '{expected_str}', got EOF")
        
        if expected_type and tok.type != expected_type:
            expected_str = expected_value if expected_value else expected_type
            raise Exception(f"SyntaxError [Line {tok.line}, Col {tok.column}]: Expected '{expected_str}', got '{tok.value}'")
            
        if expected_value and tok.value != expected_value:
            raise Exception(f"SyntaxError [Line {tok.line}, Col {tok.column}]: Expected '{expected_value}', got '{tok.value}'")
            
        self.pos += 1
        return tok

    def match(self, expected_type=None, expected_value=None) -> bool:
        tok = self.peek()
        if not tok:
            return False
        if expected_type and tok.type != expected_type:
            return False
        if expected_value and tok.value != expected_value:
            return False
        return True

    def parse(self) -> Program:
        menu = self.parse_menu_decl()
        items = []
        
        while True:
            tok = self.peek()
            if not tok:
                break
            if tok.type == 'KEYWORD' and tok.value in ('INGREDIENT', 'DISH', 'COMBO'):
                items.append(self.parse_item_decl())
            else:
                break
                
        orders = []
        tok = self.peek()
        if not tok:
            raise Exception("SyntaxError: Expected 'ORDER', got EOF")
            
        orders.append(self.parse_order_block())
        while self.peek():
            orders.append(self.parse_order_block())
            
        tok = self.peek()
        if tok:
            raise Exception(f"SyntaxError [Line {tok.line}, Col {tok.column}]: Expected EOF, got '{tok.value}'")
            
        return Program(menu=menu, items=items, orders=orders)

    def parse_menu_decl(self) -> MenuDecl:
        self.consume('KEYWORD', 'MENU')
        name = self.consume('STRING').value
        
        self.consume('ID', 'currency')
        self.consume('OP', ':')
        currency = self.consume('ID').value
        
        tax = None
        service = None
        
        while self.match('ID'):
            tok = self.peek()
            if tok.value == 'tax':
                self.consume('ID', 'tax')
                self.consume('OP', ':')
                t_tok = self.peek()
                if t_tok.type in ('INTEGER', 'FLOAT'):
                    tax = float(self.consume().value)
                else:
                    raise Exception(f"SyntaxError [Line {t_tok.line}, Col {t_tok.column}]: Expected NUMBER, got '{t_tok.value}'")
            elif tok.value == 'service':
                self.consume('ID', 'service')
                self.consume('OP', ':')
                s_tok = self.peek()
                if s_tok.type in ('INTEGER', 'FLOAT'):
                    service = float(self.consume().value)
                else:
                    raise Exception(f"SyntaxError [Line {s_tok.line}, Col {s_tok.column}]: Expected NUMBER, got '{s_tok.value}'")
            else:
                break
                
        return MenuDecl(name=name, currency=currency, tax=tax, service=service)

    def parse_item_decl(self):
        tok = self.peek()
        if tok.value == 'INGREDIENT':
            return self.parse_ingredient_decl()
        elif tok.value == 'DISH':
            return self.parse_dish_decl()
        elif tok.value == 'COMBO':
            return self.parse_combo_decl()
        else:
            raise Exception(f"SyntaxError [Line {tok.line}, Col {tok.column}]: Expected item declaration, got '{tok.value}'")

    def parse_ingredient_decl(self) -> IngredientDecl:
        self.consume('KEYWORD', 'INGREDIENT')
        name = self.consume('ID').value
        
        self.consume('ID', 'stock')
        self.consume('OP', ':')
        stock_tok = self.peek()
        if stock_tok.type in ('INTEGER', 'FLOAT'):
            stock = float(self.consume().value)
        else:
            raise Exception(f"SyntaxError [Line {stock_tok.line}, Col {stock_tok.column}]: Expected NUMBER, got '{stock_tok.value}'")
        
        stock_unit = None
        if self.match('UNIT'):
            stock_unit = self.consume('UNIT').value
            
        self.consume('ID', 'unit')
        self.consume('OP', ':')
        unit = self.consume('UNIT').value
        
        return IngredientDecl(name=name, stock=stock, stock_unit=stock_unit, unit=unit)

    def parse_dish_decl(self) -> DishDecl:
        self.consume('KEYWORD', 'DISH')
        name = self.consume('STRING').value
        
        self.consume('KEYWORD', 'NEEDS')
        needs = self.parse_need_list()
        
        self.consume('KEYWORD', 'PRICE')
        price_tok = self.peek()
        if price_tok.type in ('INTEGER', 'FLOAT'):
            price = float(self.consume().value)
        else:
            raise Exception(f"SyntaxError [Line {price_tok.line}, Col {price_tok.column}]: Expected NUMBER, got '{price_tok.value}'")
            
        prep_time = None
        if self.match('KEYWORD', 'PREP_TIME'):
            self.consume('KEYWORD', 'PREP_TIME')
            pt_tok = self.peek()
            if pt_tok.type in ('INTEGER', 'FLOAT'):
                prep_time = float(self.consume().value)
            else:
                raise Exception(f"SyntaxError [Line {pt_tok.line}, Col {pt_tok.column}]: Expected NUMBER, got '{pt_tok.value}'")
            self.consume('UNIT', 'min')
            
        self.consume('KEYWORD', 'SEASON')
        season = self.consume('SEASON').value
        
        self.consume('KEYWORD', 'END')
        
        return DishDecl(name=name, needs=needs, price=price, season=season, prep_time=prep_time)

    def parse_need_list(self) -> List[Need]:
        needs = []
        needs.append(self.parse_need())
        while self.match('OP', ','):
            self.consume('OP', ',')
            needs.append(self.parse_need())
        return needs

    def parse_need(self) -> Need:
        ingredient = self.consume('ID').value
        self.consume('OP', ':')
        amt_tok = self.peek()
        if amt_tok.type in ('INTEGER', 'FLOAT'):
            amount = float(self.consume().value)
        else:
            raise Exception(f"SyntaxError [Line {amt_tok.line}, Col {amt_tok.column}]: Expected NUMBER, got '{amt_tok.value}'")
        unit = self.consume('UNIT').value
        return Need(ingredient=ingredient, amount=amount, unit=unit)

    def parse_combo_decl(self) -> ComboDecl:
        self.consume('KEYWORD', 'COMBO')
        name = self.consume('STRING').value
        
        self.consume('KEYWORD', 'INCLUDES')
        includes = []
        includes.append(self.parse_combo_item())
        while self.match('OP', ','):
            self.consume('OP', ',')
            includes.append(self.parse_combo_item())
            
        self.consume('KEYWORD', 'DISCOUNT')
        disc_tok = self.peek()
        if disc_tok.type in ('INTEGER', 'FLOAT'):
            discount = float(self.consume().value)
        else:
            raise Exception(f"SyntaxError [Line {disc_tok.line}, Col {disc_tok.column}]: Expected NUMBER, got '{disc_tok.value}'")
        self.consume('OP', '%')
        
        self.consume('KEYWORD', 'END')
        return ComboDecl(name=name, includes=includes, discount=discount)

    def parse_combo_item(self) -> ComboItem:
        amt_tok = self.peek()
        if amt_tok.type in ('INTEGER', 'FLOAT'):
            quantity = float(self.consume().value)
        else:
            raise Exception(f"SyntaxError [Line {amt_tok.line}, Col {amt_tok.column}]: Expected NUMBER, got '{amt_tok.value}'")
            
        self.consume('OP', 'x')
        
        item_tok = self.peek()
        if item_tok.type in ('STRING', 'ID'):
            item = self.consume().value
        else:
            raise Exception(f"SyntaxError [Line {item_tok.line}, Col {item_tok.column}]: Expected STRING or ID, got '{item_tok.value}'")
            
        return ComboItem(quantity=quantity, item=item)

    def parse_order_block(self) -> OrderBlock:
        self.consume('KEYWORD', 'ORDER')
        
        table = None
        waiter = None
        date = None
        
        while self.match('ID'):
            tok = self.peek()
            if tok.value == 'table':
                self.consume('ID', 'table')
                self.consume('OP', ':')
                t_tok = self.peek()
                if t_tok.type in ('INTEGER', 'FLOAT'):
                    table = int(self.consume().value)
                else:
                    raise Exception(f"SyntaxError [Line {t_tok.line}, Col {t_tok.column}]: Expected NUMBER, got '{t_tok.value}'")
            elif tok.value == 'waiter':
                self.consume('ID', 'waiter')
                self.consume('OP', ':')
                waiter = self.consume('STRING').value
            elif tok.value == 'date':
                self.consume('ID', 'date')
                self.consume('OP', ':')
                date = self.consume('DATE').value
            else:
                break
                
        items = []
        while True:
            tok = self.peek()
            if tok and tok.type in ('INTEGER', 'FLOAT'):
                items.append(self.parse_order_item())
            else:
                break
                
        if len(items) == 0:
            tok = self.peek()
            if tok:
                raise Exception(f"SyntaxError [Line {tok.line}, Col {tok.column}]: Expected order_item, got '{tok.value}'")
            else:
                raise Exception("SyntaxError: Expected order_item, got EOF")
                
        apply_combo = None
        if self.match('KEYWORD', 'APPLY_COMBO'):
            self.consume('KEYWORD', 'APPLY_COMBO')
            apply_combo = self.consume('STRING').value
            
        self.consume('KEYWORD', 'END')
        
        return OrderBlock(table=table, waiter=waiter, date=date, items=items, apply_combo=apply_combo)

    def parse_order_item(self) -> OrderItem:
        amt_tok = self.peek()
        if amt_tok.type in ('INTEGER', 'FLOAT'):
            quantity = float(self.consume().value)
        else:
            raise Exception(f"SyntaxError [Line {amt_tok.line}, Col {amt_tok.column}]: Expected NUMBER, got '{amt_tok.value}'")
            
        self.consume('OP', 'x')
        
        item_tok = self.peek()
        if item_tok.type in ('STRING', 'ID'):
            item = self.consume().value
        else:
            raise Exception(f"SyntaxError [Line {item_tok.line}, Col {item_tok.column}]: Expected STRING or ID, got '{item_tok.value}'")
            
        return OrderItem(quantity=quantity, item=item)
