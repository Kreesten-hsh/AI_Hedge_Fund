import os
import ast
from pathlib import Path

src_dir = Path(__file__).parent

def analyze_imports():
    violations = []
    
    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith(".py"): continue
            file_path = Path(root) / file
            
            # Determine which package we are in
            rel_path = file_path.relative_to(src_dir)
            parts = rel_path.parts
            if len(parts) == 1:
                # Root package file, e.g. src/aegis_trade/domain.py
                current_package = ""
            else:
                current_package = parts[0]
                
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        module = node.module
                        if module and module.startswith("aegis_trade."):
                            # e.g. aegis_trade.dataset.domain
                            mod_parts = module.split(".")
                            if len(mod_parts) > 2:
                                target_package = mod_parts[1]
                                # If target package is different from current package, it's cross-boundary
                                # and should only import from aegis_trade.target_package
                                if target_package != current_package:
                                    violations.append({
                                        "file": str(rel_path),
                                        "import": module,
                                        "line": node.lineno,
                                        "names": [n.name for n in node.names]
                                    })
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                
    for v in violations:
        print(f"{v['file']}:{v['line']} -> from {v['import']} import {v['names']}")
        
if __name__ == "__main__":
    analyze_imports()
