from ast_nodes import Program
from symbol_table import SymbolTable, DishEntry

class ReceiptFormatter:
    def format(self, result: dict, ast_menu) -> str:
        date_str = result['date']
        if date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                try:
                    m = int(parts[1])
                    date_str = f"{parts[2]}-{months[m-1]}-{parts[0]}"
                except:
                    pass
        
        lines = []
        lines.append(f"=== RECEIPT - {ast_menu.name} ===")
        header = []
        if result['table']: header.append(f"Table: {result['table']}")
        if result['waiter']: header.append(f"Waiter: {result['waiter']}")
        if date_str: header.append(f"Date: {date_str}")
        lines.append("    ".join(header))
        lines.append("-" * 46)
        
        for item in result['line_items']:
            qty_str = f"{item['quantity']:g}x"
            amount_str = f"{item['total']:,}"
            
            name = item['name']
            if len(name) > 24: name = name[:24]
            left_part = f"{qty_str:<4}{name:<26}"
            right_part = f"PKR {amount_str:>9}"
            lines.append(f"{left_part}{right_part}")
            
        if result['combo_discount'] > 0:
            name = f"{result['combo_name']} Discount"
            if len(name) > 28: name = name[:28]
            left_part = f"{name:<30}"
            amount_str = f"-{result['combo_discount']:,}"
            right_part = f"PKR {amount_str:>9}"
            lines.append(f"{left_part}{right_part}")
            
        lines.append("-" * 46)
        
        amount_str = f"{result['subtotal']:,}"
        lines.append(f"{'Subtotal:':<30}PKR {amount_str:>9}")
        
        if result['tax_rate'] > 0:
            amount_str = f"{result['tax_amount']:,}"
            lines.append(f"Tax ({result['tax_rate']*100:g}%):".ljust(30) + f"PKR {amount_str:>9}")
            
        if result['service_rate'] > 0:
            amount_str = f"{result['service_amount']:,}"
            lines.append(f"Service ({result['service_rate']*100:g}%):".ljust(30) + f"PKR {amount_str:>9}")
            
        lines.append("-" * 46)
        
        amount_str = f"{result['grand_total']:,}"
        lines.append(f"{'TOTAL:':<30}PKR {amount_str:>9}")
        lines.append("-" * 46)
        
        return "\n".join(lines)


class KitchenTicketFormatter:
    def format(self, result: dict, symtab: SymbolTable) -> str:
        lines = []
        lines.append("=== KITCHEN TICKET ===")
        header = []
        if result['table']: header.append(f"Table: {result['table']}")
        if result['waiter']: header.append(f"Waiter: {result['waiter']}")
        if header:
            lines.append("    ".join(header))
            lines.append("")
        
        prep_items = []
        for item in result['line_items']:
            try:
                entry = symtab.lookup(item['name'])
                if isinstance(entry, DishEntry) and getattr(entry, 'prep_time', 0) > 0:
                    prep_items.append({
                        "name": item['name'],
                        "qty": item['quantity'],
                        "prep": entry.prep_time
                    })
            except:
                pass
                
        if not prep_items:
            return "=== KITCHEN TICKET ===\nNo prep items."
            
        prep_items.sort(key=lambda x: x['prep'], reverse=True)
        max_prep = prep_items[0]['prep']
        
        for i, item in enumerate(prep_items):
            name = item['name']
            if len(name) > 13: name = name[:13]
            qty_str = f"x{item['qty']:g}"
            prep_str = f"{item['prep']:g} min"
            
            line = f"  {name:<13} {qty_str:<5} {prep_str:<8}"
            if i == 0:
                line += " <- START FIRST"
            lines.append(line)
            
        lines.append("-" * 22)
        lines.append(f"  Total prep:   {max_prep:g} min (longest item)")
        
        return "\n".join(lines)
