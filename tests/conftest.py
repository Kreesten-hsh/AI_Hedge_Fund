"""Racine de configuration pytest.

Garantit que `src/` est importable même sans installation editable du paquet :
les gates (pytest, mypy) doivent pouvoir tourner sur un clone frais, sinon un
environnement partiellement installé produit des erreurs de collection qui
masquent les vrais échecs.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# `scripts/` n'est pas un paquet installé : sans la racine dans `sys.path`, un
# script reste intestable et le gate « une fonctionnalité non testée est
# inexistante » ne peut pas s'appliquer à du code qui route des ordres réels.
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
