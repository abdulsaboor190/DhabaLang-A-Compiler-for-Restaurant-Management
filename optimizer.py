from copy import deepcopy
from typing import List, Dict, Any
from collections import Counter
import fractions
import re
from ir_generator import TACInstruction, Assign, BinaryOp, Label, Jump, ConditionalJump, Param, Call, Return, Comment

class Optimizer:
    def __init__(self, instructions: List[TACInstruction]):
        self.original_instructions = deepcopy(instructions)
        self.instructions = deepcopy(instructions)
        self.report_data = {}

    def run_all(self) -> List[TACInstruction]:
        self.instructions = self.constant_folding(self.instructions)
        self.instructions = self.dead_code_elimination(self.instructions)
        self.instructions = self.strength_reduction(self.instructions)
        return self.instructions

    def is_literal(self, val: Any) -> bool:
        return isinstance(val, (int, float))

    def evaluate_binary(self, left: Any, op: str, right: Any) -> Any:
        if op == '+': return left + right
        elif op == '-': return left - right
        elif op == '*': return left * right
        elif op == '/': return left / right
        elif op == '>': return left > right
        return None

    def constant_folding(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        new_insts = []
        folded_count = 0
        examples = []
        
        before_count = len(instructions)
        
        for i, inst in enumerate(instructions):
            if isinstance(inst, BinaryOp):
                if self.is_literal(inst.left) and self.is_literal(inst.right):
                    result_val = self.evaluate_binary(inst.left, inst.op, inst.right)
                    if result_val is not None:
                        if len(new_insts) > 0 and isinstance(new_insts[-1], Comment):
                            prev_comment = new_insts[-1]
                            if '->' not in prev_comment.text:
                                prev_comment.text = f"{prev_comment.text} -> {result_val:g}"
                        
                        new_inst = Assign(inst.result, result_val)
                        new_insts.append(new_inst)
                        folded_count += 1
                        if len(examples) == 0:
                            examples.append(f"{inst.result} = {inst.left:g} * {inst.right:g}  ->  {inst.result} = {result_val:g}")
                        continue
            new_insts.append(inst)
            
        after_count = len(new_insts)
        self.report_data['Pass 1'] = {
            'Before': before_count,
            'After': after_count,
            'Folded': folded_count,
            'Example': examples[0] if examples else "None"
        }
        return new_insts

    def dead_code_elimination(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        zero_vars = set()
        for inst in instructions:
            if isinstance(inst, Assign) and inst.value == 0:
                zero_vars.add(inst.result)
        
        uses = {}
        for inst in instructions:
            if isinstance(inst, BinaryOp):
                uses[inst.left] = uses.get(inst.left, 0) + 1
                uses[inst.right] = uses.get(inst.right, 0) + 1
            elif isinstance(inst, Assign):
                uses[inst.value] = uses.get(inst.value, 0) + 1
        
        dead_zeros = set()
        dead_adds = set()
        aliases = {}
        
        for inst in instructions:
            if isinstance(inst, BinaryOp) and inst.op == '+':
                if inst.left in zero_vars and uses[inst.left] == 1:
                    dead_zeros.add(inst.left)
                    dead_adds.add(inst.result)
                    aliases[inst.result] = aliases.get(inst.right, inst.right)
                elif inst.right in zero_vars and uses[inst.right] == 1:
                    dead_zeros.add(inst.right)
                    dead_adds.add(inst.result)
                    aliases[inst.result] = aliases.get(inst.left, inst.left)
                    
        new_insts = []
        removed_comments = 0
        removed_assigns = 0
        removed_adds = 0
        
        i = 0
        while i < len(instructions):
            inst = instructions[i]
            
            if isinstance(inst, Comment) and i + 1 < len(instructions):
                next_inst = instructions[i+1]
                if isinstance(next_inst, Assign) and next_inst.result in dead_zeros:
                    removed_comments += 1
                    i += 1
                    continue
                    
            if isinstance(inst, Assign) and inst.result in dead_zeros:
                removed_assigns += 1
                i += 1
                continue
                
            if isinstance(inst, BinaryOp) and inst.result in dead_adds:
                removed_adds += 1
                i += 1
                continue
                
            if isinstance(inst, Assign):
                val = aliases.get(inst.value, inst.value)
                new_insts.append(Assign(inst.result, val))
            elif isinstance(inst, BinaryOp):
                l = aliases.get(inst.left, inst.left)
                r = aliases.get(inst.right, inst.right)
                while isinstance(l, str) and l in aliases: l = aliases[l]
                while isinstance(r, str) and r in aliases: r = aliases[r]
                new_insts.append(BinaryOp(inst.result, l, inst.op, r))
            else:
                new_insts.append(inst)
            i += 1

        renumber_map = {}
        temp_counter = 1
        final_insts = []
        
        for inst in new_insts:
            if isinstance(inst, Label):
                temp_counter = 1
                renumber_map = {}
                final_insts.append(inst)
                continue
                
            new_inst = deepcopy(inst)
            if hasattr(new_inst, 'left') and isinstance(new_inst.left, str) and re.match(r'^t\d+$', new_inst.left):
                new_inst.left = renumber_map.get(new_inst.left, new_inst.left)
            if hasattr(new_inst, 'right') and isinstance(new_inst.right, str) and re.match(r'^t\d+$', new_inst.right):
                new_inst.right = renumber_map.get(new_inst.right, new_inst.right)
            if hasattr(new_inst, 'value') and isinstance(new_inst.value, str) and re.match(r'^t\d+$', new_inst.value):
                new_inst.value = renumber_map.get(new_inst.value, new_inst.value)
                
            if hasattr(new_inst, 'result') and isinstance(new_inst.result, str) and re.match(r'^t\d+$', new_inst.result):
                new_t = f"t{temp_counter}"
                renumber_map[new_inst.result] = new_t
                new_inst.result = new_t
                temp_counter += 1
                
            final_insts.append(new_inst)

        total_removed = removed_comments + removed_assigns + removed_adds
        rem_str = f"{total_removed} instruction(s) ({removed_assigns} dead assignment + {removed_adds} dead addition"
        if removed_comments > 0:
            rem_str += f" + {removed_comments} dead comment)"
        else:
            rem_str += ")"
            
        self.report_data['Pass 2'] = {
            'Before': len(instructions),
            'After': len(final_insts),
            'Removed': rem_str,
            'TotalRemovedNum': total_removed
        }
        return final_insts

    def strength_reduction(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        new_insts = []
        reduced_count = 0
        reductions = []
        
        for inst in instructions:
            if isinstance(inst, BinaryOp):
                if inst.op == '*' and inst.right in (1, 1.0):
                    new_insts.append(Assign(inst.result, inst.left))
                    reduced_count += 1
                    reductions.append("multiply-by-1 -> direct assignment")
                    continue
                elif inst.op == '*' and inst.left in (1, 1.0):
                    new_insts.append(Assign(inst.result, inst.right))
                    reduced_count += 1
                    reductions.append("multiply-by-1 -> direct assignment")
                    continue
                    
                elif inst.op == '*' and inst.right in (0, 0.0):
                    new_insts.append(Assign(inst.result, 0))
                    reduced_count += 1
                    reductions.append("multiply-by-0 -> assign 0")
                    continue
                elif inst.op == '*' and inst.left in (0, 0.0):
                    new_insts.append(Assign(inst.result, 0))
                    reduced_count += 1
                    reductions.append("multiply-by-0 -> assign 0")
                    continue
                    
                elif inst.op == '/' and inst.right in (1, 1.0):
                    new_insts.append(Assign(inst.result, inst.left))
                    reduced_count += 1
                    reductions.append("divide-by-1 -> direct assignment")
                    continue
                    
                elif inst.op == '+' and inst.right in (0, 0.0):
                    new_insts.append(Assign(inst.result, inst.left))
                    reduced_count += 1
                    reductions.append("add-0 -> direct assignment")
                    continue
                elif inst.op == '+' and inst.left in (0, 0.0):
                    new_insts.append(Assign(inst.result, inst.right))
                    reduced_count += 1
                    reductions.append("add-0 -> direct assignment")
                    continue
                    
                if inst.op == '*' and isinstance(inst.right, float) and 0 < inst.right < 1:
                    frac = fractions.Fraction(inst.right).limit_denominator(100)
                    new_insts.append(Comment(f"Fraction equivalent: multiply by {frac.numerator}/{frac.denominator}"))

            new_insts.append(inst)

        counts = Counter(reductions)
        red_str = " + ".join(f"{v} {k}" for k, v in counts.items()) if counts else "0 reductions"
        
        self.report_data['Pass 3'] = {
            'Before': len(instructions),
            'After': len(new_insts),
            'Reduced': red_str,
            'TotalReducedNum': reduced_count
        }
        return new_insts

    def print_report(self):
        print("=== Optimization Report ===\n")
        
        p1 = self.report_data.get('Pass 1', {'Before': 0, 'After': 0, 'Folded': 0, 'Example': 'None'})
        print("Pass 1: Constant Folding")
        print(f"  Before: {p1['Before']} instructions")
        print(f"  After:  {p1['After']} instructions")
        print(f"  Folded: {p1['Folded']} binary operations -> assignments")
        print(f"  Example: {p1['Example']}\n")
        
        p2 = self.report_data.get('Pass 2', {'Before': 0, 'After': 0, 'Removed': '0 instructions', 'TotalRemovedNum': 0})
        print("Pass 2: Dead Code Elimination")
        print(f"  Before: {p2['Before']} instructions")
        print(f"  After:  {p2['After']} instructions")
        print(f"  Removed: {p2['Removed']}\n")
        
        p3 = self.report_data.get('Pass 3', {'Before': 0, 'After': 0, 'Reduced': '0 reductions', 'TotalReducedNum': 0})
        print("Pass 3: Strength Reduction")
        print(f"  Before: {p3['Before']} instructions")
        print(f"  After:  {p3['After']} instructions")
        print(f"  Reduced: {p3['Reduced']}\n")

    def pretty_print(self, instructions: List[TACInstruction]):
        print("=== Optimized TAC ===")
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
