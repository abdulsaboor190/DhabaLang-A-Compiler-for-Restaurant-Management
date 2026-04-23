from dataclasses import dataclass
from typing import Any, List
from ast_nodes import Program
from symbol_table import SymbolTable, DishEntry

# TAC Instructions
class TACInstruction:
    pass

@dataclass
class Assign(TACInstruction):
    result: str
    value: Any

@dataclass
class BinaryOp(TACInstruction):
    result: str
    left: Any
    op: str
    right: Any

@dataclass
class Label(TACInstruction):
    name: str

@dataclass
class Jump(TACInstruction):
    label: str

@dataclass
class ConditionalJump(TACInstruction):
    condition: str
    label: str

@dataclass
class Param(TACInstruction):
    value: Any

@dataclass
class Call(TACInstruction):
    result: str
    func: str
    arg_count: int

@dataclass
class Return(TACInstruction):
    value: Any

@dataclass
class Comment(TACInstruction):
    text: str

class IRGenerator:
    def __init__(self, ast: Program, symtab: SymbolTable):
        self.ast = ast
        self.symtab = symtab
        self.temp_counter = 1

    def new_temp(self) -> str:
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def generate(self) -> List[TACInstruction]:
        instructions = []
        for i, order in enumerate(self.ast.orders):
            self.temp_counter = 1
            instructions.append(Label(f"ORDER_{i+1}"))
            
            subtotals = []
            
            for item in order.items:
                entry = self.symtab.lookup(item.item)
                price = getattr(entry, 'price', 0)
                
                currency = self.symtab.menu_scope.get('currency', '')
                instructions.append(Comment(f"{item.quantity:g}x {item.item} @ {currency} {price:g}"))
                
                t = self.new_temp()
                instructions.append(BinaryOp(t, item.quantity, '*', price))
                subtotals.append(t)
                
            if subtotals:
                running_sum = self.new_temp()
                instructions.append(BinaryOp(running_sum, subtotals[0], '+', 0))
                
                for t_next in subtotals[1:]:
                    new_sum = self.new_temp()
                    instructions.append(BinaryOp(new_sum, running_sum, '+', t_next))
                    running_sum = new_sum
                    
                instructions.append(Assign("subtotal", running_sum))
            else:
                instructions.append(Assign("subtotal", 0))
                
            current_subtotal = "subtotal"
            if order.apply_combo:
                combo_entry = self.symtab.lookup(order.apply_combo)
                discount_percent = combo_entry.discount_percent
                discount_frac = discount_percent / 100.0
                
                instructions.append(Comment(f"Apply combo: {combo_entry.name} ({discount_percent:g}%)"))
                t_disc = self.new_temp()
                instructions.append(BinaryOp(t_disc, current_subtotal, '*', discount_frac))
                instructions.append(BinaryOp("subtotal_after_discount", current_subtotal, '-', t_disc))
                current_subtotal = "subtotal_after_discount"
                
            tax_rate = self.symtab.menu_scope.get('tax') or 0
            if tax_rate > 0:
                instructions.append(Comment(f"Tax ({tax_rate*100:g}%)"))
            else:
                instructions.append(Comment("Tax (0%)"))
            t_tax = self.new_temp()
            instructions.append(BinaryOp(t_tax, current_subtotal, '*', tax_rate))
            
            service_rate = self.symtab.menu_scope.get('service') or 0
            if service_rate > 0:
                instructions.append(Comment(f"Service charge ({service_rate*100:g}%)"))
            else:
                instructions.append(Comment("Service charge (0%)"))
            t_service = self.new_temp()
            instructions.append(BinaryOp(t_service, current_subtotal, '*', service_rate))
            
            instructions.append(Comment("Final total"))
            t_total_temp = self.new_temp()
            instructions.append(BinaryOp(t_total_temp, current_subtotal, '+', t_tax))
            t_total = self.new_temp()
            instructions.append(BinaryOp(t_total, t_total_temp, '+', t_service))
            instructions.append(Assign("TOTAL", t_total))
            
        return instructions

    def pretty_print(self, instructions: List[TACInstruction]):
        print("=== Three-Address Code ===")
        for instr in instructions:
            if isinstance(instr, Label):
                print(f"\n{instr.name}:")
            elif isinstance(instr, Comment):
                print(f"  # {instr.text}")
            elif isinstance(instr, Assign):
                print(f"  {instr.result} = {instr.value}")
            elif isinstance(instr, BinaryOp):
                print(f"  {instr.result} = {instr.left} {instr.op} {instr.right}")
            elif isinstance(instr, Jump):
                print(f"  goto {instr.label}")
            elif isinstance(instr, ConditionalJump):
                print(f"  if {instr.condition} goto {instr.label}")
            elif isinstance(instr, Param):
                print(f"  param {instr.value}")
            elif isinstance(instr, Call):
                print(f"  {instr.result} = call {instr.func}, {instr.arg_count}")
            elif isinstance(instr, Return):
                print(f"  return {instr.value}")
