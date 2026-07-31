"""Racine de configuration pytest.

Garantit que `src/` est importable même sans installation editable du paquet :
les gates (pytest, mypy) doivent pouvoir tourner sur un clone frais, sinon un
environnement partiellement installé produit des erreurs de collection qui
masquent les vrais échecs.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
