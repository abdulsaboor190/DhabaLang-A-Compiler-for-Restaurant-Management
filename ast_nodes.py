from dataclasses import dataclass
from typing import List, Optional, Union, Any

def to_dict(obj: Any) -> Any:
    if hasattr(obj, '__dataclass_fields__'):
        d = {"type": obj.__class__.__name__}
        for k in obj.__dataclass_fields__:
            d[k] = to_dict(getattr(obj, k))
        return d
    elif isinstance(obj, list):
        return [to_dict(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    else:
        return obj

@dataclass
class Node:
    pass

@dataclass
class MenuDecl(Node):
    name: str
    currency: str
    tax: Optional[float] = None
    service: Optional[float] = None

@dataclass
class IngredientDecl(Node):
    name: str
    stock: float
    stock_unit: Optional[str]
    unit: str

@dataclass
class Need(Node):
    ingredient: str
    amount: float
    unit: str

@dataclass
class DishDecl(Node):
    name: str
    needs: List[Need]
    price: float
    season: str
    prep_time: Optional[float] = None

@dataclass
class ComboItem(Node):
    quantity: float
    item: str

@dataclass
class ComboDecl(Node):
    name: str
    includes: List[ComboItem]
    discount: float

@dataclass
class OrderItem(Node):
    quantity: float
    item: str

@dataclass
class OrderBlock(Node):
    items: List[OrderItem]
    table: Optional[int] = None
    waiter: Optional[str] = None
    date: Optional[str] = None
    apply_combo: Optional[str] = None

@dataclass
class Program(Node):
    menu: MenuDecl
    items: List[Union[IngredientDecl, DishDecl, ComboDecl]]
    orders: List[OrderBlock]
