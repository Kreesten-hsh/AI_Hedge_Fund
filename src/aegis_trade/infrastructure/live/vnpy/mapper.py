"""Traduction des symboles entre le domaine Aegis et vn.py.

La fidélité de l'aller-retour n'est pas cosmétique : un ordre part avec
`Symbol(name, asset_class)`, le fill revient identifié par une chaîne vn.py.
Si le `Symbol` reconstruit diffère ne serait-ce que par sa classe d'actif, le
`Portfolio` ouvre une seconde position fantôme au lieu d'alimenter celle que
l'ordre a créée — et le risque calculé porte alors sur une exposition fausse.
"""

from __future__ import annotations

from aegis_trade.domain.core import AssetClass, Symbol


class VnPySymbolMapper:
    """Traduit les symboles Aegis en symboles de gateway vn.py.

    Exemple : `BTCUSDT` -> `BTCUSDT.BINANCE`.
    """

    def __init__(
        self,
        default_exchange: str,
        default_asset_class: AssetClass = AssetClass.CRYPTO,
    ) -> None:
        self.default_exchange = default_exchange
        # Classe d'actif appliquée aux symboles jamais vus à l'aller (ticks
        # d'un instrument non tradé, reprise après redémarrage). Déclarée à la
        # construction plutôt que devinée symbole par symbole.
        self.default_asset_class = default_asset_class
        self._known: dict[str, Symbol] = {}

    def register(self, aegis_symbol: Symbol) -> None:
        """Mémorise un symbole pour que le retour de vn.py soit exact."""
        self._known[aegis_symbol.name] = aegis_symbol

    def to_vnpy_symbol(self, aegis_symbol: Symbol) -> str:
        # vn.py utilise le format 'symbol.EXCHANGE' : 'AAPL.SMART',
        # 'BTCUSDT.BINANCE'.
        self.register(aegis_symbol)
        return f"{aegis_symbol.name}.{self.default_exchange}"

    def from_vnpy_symbol(self, vnpy_symbol: str) -> Symbol:
        """Reconstruit le `Symbol` du domaine à partir d'un `vt_symbol`.

        Renvoie l'instance exacte déjà traduite à l'aller quand elle existe :
        c'est ce qui garantit l'égalité de valeur côté `Portfolio`.
        """
        name = vnpy_symbol.split(".")[0]
        if not name:
            raise ValueError(f"Invalid vnpy symbol format: {vnpy_symbol!r}")

        known = self._known.get(name)
        if known is not None:
            return known
        return Symbol(name=name, asset_class=self.default_asset_class)
