import os
import ast
from pathlib import Path

def get_flagged_files(src_dir: Path) -> list[str]:
    """Finds all python files in src_dir containing the scientific warning."""
    warning_text = "AVERTISSEMENT DE DISCIPLINE SCIENTIFIQUE"
    flagged = []
    
    for filepath in src_dir.rglob("*.py"):
        try:
            content = filepath.read_text(encoding="utf-8")
            if warning_text in content:
                # Convert path to module name (e.g. aegis_trade.strategies.macro_dxy)
                rel_path = filepath.relative_to(src_dir)
                module_name = str(rel_path.with_suffix("")).replace(os.sep, ".")
                flagged.append(module_name)
        except Exception:
            pass
    return flagged

def get_imported_modules(script_path: Path) -> list[str]:
    """Extracts all imported module names from a python script using AST."""
    if not script_path.exists():
        return []
        
    content = script_path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
                
    return imports

def test_no_unvalidated_signals_in_production():
    """
    Ensures that production scripts do not import unvalidated hypothesis modules.
    """
    root_dir = Path(__file__).parent.parent
    src_dir = root_dir / "src"
    scripts_dir = root_dir / "scripts"
    
    flagged_modules = get_flagged_files(src_dir)
    
    # Scripts that could touch real or simulated money
    production_scripts = [
        scripts_dir / "run_paper_trading.py",
        scripts_dir / "run_risk_governance.py"
    ]
    
    violations = []
    
    for script in production_scripts:
        if not script.exists():
            continue
            
        imports = get_imported_modules(script)
        
        for imp in imports:
            for flagged in flagged_modules:
                # If the script imports a flagged module or its parent package
                # (e.g. importing `aegis_trade.strategies.macro_dxy` or `from aegis_trade.strategies import macro_dxy`)
                if imp.startswith(flagged) or flagged.startswith(imp):
                    # We have to be careful with `flagged.startswith(imp)`.
                    # If script does `import aegis_trade.agents`, that covers unvalidated agents.
                    # Let's just do a strict matching of the module prefix.
                    if flagged.startswith(imp) or imp.startswith(flagged):
                         violations.append(f"Script {script.name} imports unvalidated module: {imp} (matches {flagged})")

    assert not violations, "\n".join(violations)
