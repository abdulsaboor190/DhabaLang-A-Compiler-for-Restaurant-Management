import json
import os
from datetime import datetime
from collections import defaultdict
from ir_generator import TACInstruction, Assign, BinaryOp, Label, Comment
from ast_nodes import Program
from symbol_table import SymbolTable, DishEntry, IngredientEntry

class DiagnosticsCollector:
    def __init__(self):
        self.diagnostics = []
        
    def add_warning(self, line: int, message: str):
        self.diagnostics.append(f"  WARNING  [Line {line:02d}]: {message}")
        
    def add_info(self, line: int, message: str):
        self.diagnostics.append(f"  INFO     [Line {line:02d}]: {message}")
        
    def add_error(self, message: str):
        self.diagnostics.append(f"  ERROR    {message}")
        
    def print_diagnostics(self, success: bool, error_count: int = 0):
        print("=== Compiler Diagnostics ===")
        for d in self.diagnostics:
            print(d)
        print()
        if success:
            print("Compilation: SUCCESS")
        else:
            print(f"Compilation: FAILED ({error_count} error{'s' if error_count != 1 else ''})")


class CodeGenerator:
    def __init__(self, instructions: list, ast: Program, symtab: SymbolTable, diagnostics: DiagnosticsCollector):
        self.instructions = instructions
        self.ast = ast
        self.symtab = symtab
        self.diagnostics = diagnostics
        self.results = []

    def run(self):
        current_order = None
        var_store = {}
        order_idx = -1
        
        for inst in self.instructions:
            if isinstance(inst, Label):
                if current_order is not None:
                    self._finalize_order(current_order, var_store, order_idx)
                current_order = inst.name
                order_idx += 1
                var_store = {}
            elif isinstance(inst, Assign):
                val = var_store.get(inst.value, inst.value) if isinstance(inst.value, str) else inst.value
                var_store[inst.result] = val
            elif isinstance(inst, BinaryOp):
                left = var_store.get(inst.left, inst.left) if isinstance(inst.left, str) else inst.left
                right = var_store.get(inst.right, inst.right) if isinstance(inst.right, str) else inst.right
                if inst.op == '+': res = left + right
                elif inst.op == '-': res = left - right
                elif inst.op == '*': res = left * right
                elif inst.op == '/': res = left / right
                else: res = 0
                var_store[inst.result] = res
                
        if current_order is not None:
            self._finalize_order(current_order, var_store, order_idx)
            
        return self.results
        
    def _finalize_order(self, label: str, var_store: dict, order_idx: int):
        ast_order = self.ast.orders[order_idx]
        
        line_items = []
        for item in ast_order.items:
            if item.quantity == 0:
                continue
            try:
                entry = self.symtab.lookup(item.item)
                price = getattr(entry, 'price', 0)
                total = item.quantity * price
                line_items.append({
                    "name": item.item,
                    "quantity": item.quantity,
                    "unit_price": round(price),
                    "total": round(total)
                })
            except:
                pass
                
        combo_name = None
        combo_discount = 0
        if ast_order.apply_combo:
            combo_name = ast_order.apply_combo
            combo_discount = var_store.get('subtotal', 0) - var_store.get('subtotal_after_discount', var_store.get('subtotal', 0))
            if combo_discount > 0:
                self.diagnostics.add_info(0, f"Combo '{combo_name}' applied. Discount: PKR {round(combo_discount)}.")
            
        tax_rate = self.ast.menu.tax or 0
        tax_amount = var_store.get('subtotal_after_discount', var_store.get('subtotal', 0)) * tax_rate
        
        service_rate = self.ast.menu.service or 0
        service_amount = var_store.get('subtotal_after_discount', var_store.get('subtotal', 0)) * service_rate
        
        res = {
            "order_label": label,
            "table": ast_order.table,
            "waiter": ast_order.waiter,
            "date": ast_order.date,
            "line_items": line_items,
            "subtotal": round(var_store.get('subtotal', 0)),
            "combo_name": combo_name,
            "combo_discount": round(combo_discount),
            "tax_rate": tax_rate,
            "tax_amount": round(tax_amount),
            "service_rate": service_rate,
            "service_amount": round(service_amount),
            "grand_total": round(var_store.get('TOTAL', 0))
        }
        self.results.append(res)
        
    def write_log(self, source_file: str) -> str:
        log_path = os.path.splitext(source_file)[0] + ".log"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        original_stock = {}
        units = {}
        for item in self.ast.items:
            if type(item).__name__ == 'IngredientDecl':
                original_stock[item.name] = item.stock
                units[item.name] = item.unit
                
        current_stock = dict(original_stock)
        grand_total_consumed = {k: 0 for k in original_stock}
        
        lines = []
        lines.append("=== DhabaLang Ingredient Log ===")
        lines.append(f"Source: {os.path.basename(source_file)}")
        lines.append(f"Generated: {now_str}\n")
        
        for idx, order in enumerate(self.ast.orders):
            res = self.results[idx]
            table_str = f"Table: {res['table']}" if res['table'] else "Table: N/A"
            date_str = f"Date: {res['date']}" if res['date'] else "Date: N/A"
            
            if res['date']:
                parts = res['date'].split('-')
                if len(parts) == 3:
                    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    try:
                        m = int(parts[1])
                        date_str = f"Date: {parts[2]}-{months[m-1]}-{parts[0]}"
                    except:
                        pass
                        
            lines.append(f"{res['order_label']} | {table_str} | {date_str}")
            
            consumed_this_order = defaultdict(float)
            for item in order.items:
                try:
                    entry = self.symtab.lookup(item.item)
                    if isinstance(entry, DishEntry):
                        for need in entry.needs:
                            consumed_this_order[need.ingredient] += need.amount * item.quantity
                    elif isinstance(entry, IngredientEntry):
                        consumed_this_order[entry.name] += item.quantity
                except:
                    pass
                    
            for ing_name in original_stock:
                cons = consumed_this_order[ing_name]
                if cons > 0:
                    current_stock[ing_name] -= cons
                    grand_total_consumed[ing_name] += cons
                    unit = units[ing_name]
                    unit_str = f" {unit}" if unit == "piece" or unit == "pieces" else unit
                    if unit == "piece": unit_str = " pieces"
                    
                    lines.append(f"  {ing_name:<11} consumed: {cons:g}{unit_str:<7} remaining: {current_stock[ing_name]:g}{unit_str}")
            lines.append("")
            
        lines.append("GRAND TOTAL CONSUMED (all orders):")
        for ing_name, total in grand_total_consumed.items():
            if total > 0:
                unit = units[ing_name]
                unit_str = f" {unit}" if unit == "piece" or unit == "pieces" else unit
                if unit == "piece": unit_str = " pieces"
                lines.append(f"  {ing_name:<11} total: {total:g}{unit_str}")
                
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")
            
        return log_path

    def export_json(self, output_path: str):
        out = {
            "restaurant": self.ast.menu.name,
            "currency": self.ast.menu.currency,
            "orders": []
        }
        for res in self.results:
            order = {
                "label": res["order_label"],
                "table": res["table"],
                "waiter": res["waiter"],
                "date": res["date"],
                "items": [{"name": i["name"], "qty": i["quantity"], "unit_price": i["unit_price"], "total": i["total"]} for i in res["line_items"]],
                "subtotal": res["subtotal"],
                "discount": {"combo": res["combo_name"], "amount": res["combo_discount"]} if res["combo_name"] else None,
                "tax": {"rate": res["tax_rate"], "amount": res["tax_amount"]},
                "service": {"rate": res["service_rate"], "amount": res["service_amount"]},
                "grand_total": res["grand_total"]
            }
            out["orders"].append(order)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2)
