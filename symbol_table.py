from dataclasses import dataclass
from typing import Dict, List, Optional, Any

@dataclass
class IngredientEntry:
    name: str
    stock: float
    unit: str

@dataclass
class DishEntry:
    name: str
    price: float
    prep_time: Optional[float]
    needs: List[Any]
    season: str

@dataclass
class ComboEntry:
    name: str
    includes: List[Any]
    discount_percent: float

@dataclass
class OrderEntry:
    table: Optional[int]
    waiter: Optional[str]
    date: Optional[str]
    items: List[Any]
    applied_combo: Optional[str]

class SemanticError(Exception):
    pass

class SymbolTable:
    def __init__(self):
        self.menu_scope = {}
        self.declaration_scope = {}
        self.order_scope = []

    def declare(self, name: str, entry: Any):
        if name in self.declaration_scope:
            raise SemanticError(f"Duplicate declaration for '{name}'")
        self.declaration_scope[name] = entry

    def lookup(self, name: str) -> Any:
        if name not in self.declaration_scope:
            raise SemanticError(f"Undefined reference '{name}'")
        return self.declaration_scope[name]

    def dump(self):
        print("=== Symbol Table Dump ===")
        print("Menu Scope:")
        for k, v in self.menu_scope.items():
            print(f"  {k}: {v}")
        print("\nDeclaration Scope:")
        for k, v in self.declaration_scope.items():
            print(f"  {k}: {v}")
        print("\nOrder Scope:")
        for i, order in enumerate(self.order_scope):
            print(f"  Order {i+1}: {order}")
        print("=========================")
