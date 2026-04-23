import sys
from typing import List, Tuple, Any
from symbol_table import SymbolTable, IngredientEntry, DishEntry, ComboEntry, OrderEntry, SemanticError
from ast_nodes import Program, IngredientDecl, DishDecl, ComboDecl, OrderBlock

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]

def get_season(month: int) -> str:
    if month in (12, 1, 2):
        return 'winter'
    elif month in (3, 4, 5):
        return 'all_year'
    elif month in (6, 7, 8):
        return 'summer'
    elif month in (9, 10, 11):
        return 'monsoon'
    return 'all_year'

class SemanticAnalyzer:
    def __init__(self, ast: Program, tokens: list):
        self.ast = ast
        self.tokens = tokens
        self.symtab = SymbolTable()
        self.errors = []
        self.warnings = []

    def get_block_start(self, keyword: str, block_idx: int) -> Tuple[int, int]:
        count = 0
        for tok in self.tokens:
            if tok.type == 'KEYWORD' and tok.value == keyword:
                if count == block_idx:
                    return tok.line, tok.column
                count += 1
        return 0, 0

    def find_token_pos(self, keyword: str, block_idx: int, target_value: Any, expected_type: str = None) -> Tuple[int, int]:
        count = 0
        start_idx = 0
        for i, tok in enumerate(self.tokens):
            if tok.type == 'KEYWORD' and tok.value == keyword:
                if count == block_idx:
                    start_idx = i
                    break
                count += 1
                
        for i in range(start_idx, len(self.tokens)):
            if i > start_idx and self.tokens[i].type == 'KEYWORD' and self.tokens[i].value == keyword:
                break
            
            tok = self.tokens[i]
            if expected_type and tok.type != expected_type:
                continue
                
            if isinstance(target_value, float):
                try:
                    if float(tok.value) == target_value:
                        return tok.line, tok.column
                except ValueError:
                    pass
            else:
                if str(tok.value) == str(target_value):
                    return tok.line, tok.column
        return 0, 0

    def analyze(self):
        try:
            self.build_symbol_table()
            self.check_type_and_values()
            self.check_references()
            self.process_orders()
        except SemanticError as e:
            self.errors.append(str(e))
        except Exception as e:
            self.errors.append(str(e))
            
        return len(self.errors) == 0

    def build_symbol_table(self):
        self.symtab.menu_scope = {
            'name': self.ast.menu.name,
            'currency': self.ast.menu.currency,
            'tax': self.ast.menu.tax,
            'service': self.ast.menu.service
        }

        for i, item in enumerate(self.ast.items):
            if type(item).__name__ == 'IngredientDecl':
                entry = IngredientEntry(name=item.name, stock=item.stock, unit=item.unit)
                try:
                    self.symtab.declare(item.name, entry)
                except SemanticError:
                    ing_idx = sum(1 for x in self.ast.items[:i] if type(x).__name__ == 'IngredientDecl')
                    line, col = self.find_token_pos('INGREDIENT', ing_idx, item.name)
                    if line == 0: line, col = self.get_block_start('INGREDIENT', ing_idx)
                    raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Duplicate declaration for '{item.name}'")

            elif type(item).__name__ == 'DishDecl':
                entry = DishEntry(name=item.name, price=item.price, prep_time=item.prep_time, needs=item.needs, season=item.season)
                try:
                    self.symtab.declare(item.name, entry)
                except SemanticError:
                    dish_idx = sum(1 for x in self.ast.items[:i] if type(x).__name__ == 'DishDecl')
                    line, col = self.find_token_pos('DISH', dish_idx, item.name)
                    if line == 0: line, col = self.get_block_start('DISH', dish_idx)
                    raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Duplicate declaration for '{item.name}'")

            elif type(item).__name__ == 'ComboDecl':
                entry = ComboEntry(name=item.name, includes=item.includes, discount_percent=item.discount)
                try:
                    self.symtab.declare(item.name, entry)
                except SemanticError:
                    combo_idx = sum(1 for x in self.ast.items[:i] if type(x).__name__ == 'ComboDecl')
                    line, col = self.find_token_pos('COMBO', combo_idx, item.name)
                    if line == 0: line, col = self.get_block_start('COMBO', combo_idx)
                    raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Duplicate declaration for '{item.name}'")

    def check_type_and_values(self):
        menu = self.ast.menu
        if menu.tax is not None and not (0 <= menu.tax <= 1):
            raise SemanticError(f"SemanticError [Line 1, Col 1]: Tax rate must be between 0 and 1")
        if menu.service is not None and not (0 <= menu.service <= 1):
            raise SemanticError(f"SemanticError [Line 1, Col 1]: Service charge rate must be between 0 and 1")
            
        ing_idx, dish_idx, combo_idx = 0, 0, 0
        for item in self.ast.items:
            if type(item).__name__ == 'IngredientDecl':
                if item.stock <= 0:
                    line, col = self.find_token_pos('INGREDIENT', ing_idx, item.stock)
                    if line == 0: line, col = self.get_block_start('INGREDIENT', ing_idx)
                    raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Stock value must be positive")
                ing_idx += 1
            elif type(item).__name__ == 'DishDecl':
                if item.price <= 0:
                    line, col = self.find_token_pos('DISH', dish_idx, item.price)
                    if line == 0: line, col = self.get_block_start('DISH', dish_idx)
                    raise SemanticError(f"SemanticError [Line {line}, Col {col}]: PRICE must be positive")
                for need in item.needs:
                    if need.amount <= 0:
                        line, col = self.find_token_pos('DISH', dish_idx, need.amount)
                        if line == 0: line, col = self.get_block_start('DISH', dish_idx)
                        raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Need amount must be positive")
                dish_idx += 1
            elif type(item).__name__ == 'ComboDecl':
                if not (0 <= item.discount <= 100):
                    line, col = self.find_token_pos('COMBO', combo_idx, item.discount)
                    if line == 0: line, col = self.get_block_start('COMBO', combo_idx)
                    raise SemanticError(f"SemanticError [Line {line}, Col {col}]: DISCOUNT must be between 0 and 100")
                for citem in item.includes:
                    if citem.quantity <= 0:
                        line, col = self.find_token_pos('COMBO', combo_idx, citem.quantity)
                        if line == 0: line, col = self.get_block_start('COMBO', combo_idx)
                        raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Combo quantity must be positive")
                combo_idx += 1
                
        for order_idx, order in enumerate(self.ast.orders):
            for order_item in order.items:
                if order_item.quantity < 0:
                    line, col = self.find_token_pos('ORDER', order_idx, order_item.quantity)
                    if line == 0: line, col = self.get_block_start('ORDER', order_idx)
                    raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Order quantity must be positive")

    def check_references(self):
        dish_idx = 0
        for item in self.ast.items:
            if type(item).__name__ == 'DishDecl':
                for need in item.needs:
                    try:
                        self.symtab.lookup(need.ingredient)
                    except SemanticError:
                        line, col = self.find_token_pos('DISH', dish_idx, need.ingredient)
                        if line == 0: line, col = self.get_block_start('DISH', dish_idx)
                        raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Ingredient '{need.ingredient}' is not defined.")
                dish_idx += 1
                
        for order_idx, order in enumerate(self.ast.orders):
            for order_item in order.items:
                try:
                    self.symtab.lookup(order_item.item)
                except SemanticError:
                    line, col = self.find_token_pos('ORDER', order_idx, order_item.item)
                    if line == 0: line, col = self.get_block_start('ORDER', order_idx)
                    raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Dish '{order_item.item}' is not defined.")
                    
            if order.apply_combo:
                try:
                    self.symtab.lookup(order.apply_combo)
                except SemanticError:
                    line, col = self.find_token_pos('ORDER', order_idx, order.apply_combo)
                    if line == 0: line, col = self.get_block_start('ORDER', order_idx)
                    raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Combo '{order.apply_combo}' is not defined.")

    def process_orders(self):
        for order_idx, order in enumerate(self.ast.orders):
            order_entry = OrderEntry(
                table=order.table,
                waiter=order.waiter,
                date=order.date,
                items=order.items,
                applied_combo=order.apply_combo
            )
            self.symtab.order_scope.append(order_entry)
            
            order_month = None
            order_year = None
            if order.date:
                parts = order.date.split('-')
                if len(parts) == 3:
                    order_year = parts[0]
                    order_month = int(parts[1])
            
            order_counts = {}
            for o_item in order.items:
                order_counts[o_item.item] = order_counts.get(o_item.item, 0) + o_item.quantity
                
                if order_month:
                    try:
                        entry = self.symtab.lookup(o_item.item)
                        if isinstance(entry, DishEntry):
                            dish_season = entry.season
                            actual_season = get_season(order_month)
                            if dish_season != 'all_year' and dish_season != actual_season:
                                m_name = MONTH_NAMES[order_month - 1]
                                line, col = self.find_token_pos('ORDER', order_idx, o_item.item)
                                if line == 0: line, col = self.get_block_start('ORDER', order_idx)
                                self.warnings.append(f"WARNING [Line {line}]: '{o_item.item}' is a {dish_season} dish. Order date is {m_name} {order_year}. Proceeding with override.")
                    except SemanticError:
                        pass 

            if order.apply_combo:
                combo_entry = self.symtab.lookup(order.apply_combo)
                for inc in combo_entry.includes:
                    found = order_counts.get(inc.item, 0)
                    if found < inc.quantity:
                        line, col = self.find_token_pos('ORDER', order_idx, order.apply_combo)
                        if line == 0: line, col = self.get_block_start('ORDER', order_idx)
                        raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Combo '{combo_entry.name}' requires {inc.quantity:g}x {inc.item} but only {found:g}x found in order.")

            for o_item in order.items:
                entry = self.symtab.lookup(o_item.item)
                quantity = o_item.quantity
                
                if isinstance(entry, DishEntry):
                    for need in entry.needs:
                        ing_entry = self.symtab.lookup(need.ingredient)
                        consumed = need.amount * quantity
                        if ing_entry.stock < consumed:
                            line, col = self.find_token_pos('ORDER', order_idx, o_item.item)
                            if line == 0: line, col = self.get_block_start('ORDER', order_idx)
                            needed_str = f"{consumed:g}{need.unit}"
                            rem_str = f"{ing_entry.stock:g}{ing_entry.unit}"
                            raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Ingredient '{need.ingredient}' stock exhausted. Needed {needed_str}, only {rem_str} remaining.")
                        ing_entry.stock -= consumed
                        
                elif isinstance(entry, IngredientEntry):
                    consumed = quantity
                    if entry.stock < consumed:
                        line, col = self.find_token_pos('ORDER', order_idx, o_item.item)
                        if line == 0: line, col = self.get_block_start('ORDER', order_idx)
                        needed_str = f"{consumed:g}{entry.unit}"
                        rem_str = f"{entry.stock:g}{entry.unit}"
                        raise SemanticError(f"SemanticError [Line {line}, Col {col}]: Ingredient '{entry.name}' stock exhausted. Needed {needed_str}, only {rem_str} remaining.")
                    entry.stock -= consumed
