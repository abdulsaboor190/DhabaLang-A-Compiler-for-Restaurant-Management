import argparse
import sys
import json
from lexer import Lexer
from parser import Parser
from ast_nodes import to_dict

def main():
    arg_parser = argparse.ArgumentParser(description="DhabaLang Compiler Phase 1")
    arg_parser.add_argument('file', help="Source file (.dhaba)")
    arg_parser.add_argument('--tokens', action='store_true', help="Print token stream")
    arg_parser.add_argument('--ast', action='store_true', help="Print AST as JSON")
    arg_parser.add_argument('--symbols', action='store_true', help="Print symbol table")
    arg_parser.add_argument('--tac', action='store_true', help="Print IR TAC")
    arg_parser.add_argument('--optimize', action='store_true', help="Run optimization and print optimized TAC")
    arg_parser.add_argument('--report', action='store_true', help="Print optimization report")
    arg_parser.add_argument('--json', action='store_true', help="Export output to JSON")
    arg_parser.add_argument('--debug', action='store_true', help="Print every phase output")
    
    args = arg_parser.parse_args()
    
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.")
        sys.exit(1)
        
    try:
        from codegen import DiagnosticsCollector, CodeGenerator
        from formatter import ReceiptFormatter, KitchenTicketFormatter
        import os
        
        diagnostics = DiagnosticsCollector()
        
        lexer = Lexer(source)
        if args.tokens or args.debug:
            if args.debug: print("=== Phase 1: Tokens ===")
            for tok in lexer.tokens:
                print(f"Token(type={tok.type}, value='{tok.value}', line={tok.line}, col={tok.column})")
                
        parser = Parser(lexer.tokens)
        ast = parser.parse()
        
        if args.ast or args.debug:
            if args.debug: print("\n=== Phase 1: AST ===")
            print(json.dumps(to_dict(ast), indent=2))
            
        from semantic import SemanticAnalyzer
        analyzer = SemanticAnalyzer(ast, lexer.tokens)
        success = analyzer.analyze()
        
        import re
        for w in analyzer.warnings:
            match = re.search(r'\[Line (\d+)\]:\s*(.*)', w)
            if match:
                diagnostics.add_warning(int(match.group(1)), match.group(2))
            else:
                diagnostics.diagnostics.append(f"  WARNING  {w}")
                
        if not success:
            for e in analyzer.errors:
                diagnostics.diagnostics.append(f"  ERROR    {e}")
            diagnostics.print_diagnostics(False, len(analyzer.errors))
            sys.exit(1)
            
        if args.symbols or args.debug:
            if args.debug: print("\n=== Phase 2: Symbol Table ===")
            analyzer.symtab.dump()
            
        from ir_generator import IRGenerator
        generator = IRGenerator(ast, analyzer.symtab)
        instructions = generator.generate()
        
        if args.tac or args.debug:
            if args.debug: print("\n=== Phase 3: Raw TAC ===")
            generator.pretty_print(instructions)
            
        from optimizer import Optimizer
        opt = Optimizer(instructions)
        optimized_insts = opt.run_all()
        
        if args.report:
            opt.print_report()
            
        if args.optimize or args.debug:
            if args.debug: print("\n=== Phase 4: Optimized TAC ===")
            opt.pretty_print(optimized_insts)
            
        codegen = CodeGenerator(optimized_insts, ast, analyzer.symtab, diagnostics)
        codegen.run()
        
        removed = opt.report_data.get('Pass 2', {}).get('TotalRemovedNum', 0)
        diagnostics.add_info(0, f"Dead code elimination removed {removed} items.")
        
        if args.json:
            json_path = os.path.splitext(args.file)[0] + ".json"
            codegen.export_json(json_path)
            
        if not any([args.tokens, args.ast, args.symbols, args.tac, args.optimize, args.report, args.json]) or args.debug:
            if args.debug: print("\n=== Phase 5: Receipt Output ===")
            print("=== DhabaLang Compiler v1.0 ===")
            print("Parsing:           OK")
            num_dishes = sum(1 for item in ast.items if type(item).__name__ == 'DishDecl')
            num_ingredients = sum(1 for item in ast.items if type(item).__name__ == 'IngredientDecl')
            num_combos = sum(1 for item in ast.items if type(item).__name__ == 'ComboDecl')
            print(f"Semantic Analysis: OK ({num_dishes} dishes, {num_ingredients} ingredients, {num_combos} combos)")
            print(f"IR Generation:     OK ({len(instructions)} instructions)")
            before_count = len(instructions)
            after_count = len(optimized_insts)
            print(f"Optimization:      OK ({before_count} -> {after_count} instructions, {removed} removed)")
            print("Code Generation:   OK\n")
            
            for res in codegen.results:
                print(ReceiptFormatter().format(res, ast.menu))
                print("\n")
                print(KitchenTicketFormatter().format(res, analyzer.symtab))
                print("\n")
                
            diagnostics.print_diagnostics(True)
            log_path = codegen.write_log(args.file)
            print(f"Log written to: {os.path.basename(log_path)}")
    except Exception:
        raise

if __name__ == '__main__':
    main()
