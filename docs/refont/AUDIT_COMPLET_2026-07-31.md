# AUDIT COMPLET — AEGIS QUANT OS

**Date** : 2026-07-31
**Branche** : `claude-code-takeover` (aucun travail sur `main`)
**Périmètre** : `src/aegis_trade/`, `frontend/`, `docs/`, `tests/`, `scripts/`, `deploy/`, historique git complet
**Verdict global** : **NO-GO** — le système ne fonctionne pas de bout en bout. Aucune couche n'est validée au sens du pipeline `CLAUDE.md`.

> Ce document est la version intégrale de l'audit de reprise. Rien n'y est omis :
> chaque affirmation est adossée à un `fichier:ligne`, une sortie de commande ou un sha de commit.
> Toute affirmation du brief de passation a été traitée comme une piste à vérifier, pas comme un fait acquis.

---

## §0 — MÉTHODE, OUTILS, LIMITES DÉCLARÉES

### Environnement mesuré

| Élément | Valeur constatée |
|---|---|
| Python | 3.11.15 (`.venv/bin/python`) |
| Gestionnaire | uv 0.12.0, `uv.lock` présent (307 pins) |
| mypy | 2.3.0 |
| pytest | 9.1.1 |
| ruff | 0.15.22 |
| Frontend | React 19 + Vite, oxlint, lightweight-charts, zustand, recharts, @tanstack/react-query |

`uv run` a été volontairement évité pendant tout l'audit : cette commande synchronise
l'environnement, donc mute l'état. Les binaires ont été invoqués directement via `.venv/bin/*`.

### Sous-agents invoqués (ordre du brief)

1. `architecture-guardian`
2. `security-dependency-auditor`
3. `quality-gatekeeper`
4. `code-review-critic`
5. `release-integrity`

`roadmap-sentinel` n'a pas été invoqué : le brief le réserve à l'après-rapport.

### Écritures effectuées pendant l'audit (divulgation intégrale)

Deux modifications hors code source, aucune sur le code applicatif :

1. **Six fichiers de configuration utilisateur globaux** `/home/hasashi/.claude/agents/*.md` :
   le frontmatter `tools:` était en minuscules (`read, grep, glob, bash`), ce qui résolvait
   zéro outil et faisait refuser le spawn (`unrecognized [read, grep, glob, bash]`).
   Corrigé en noms canoniques capitalisés (`Read, Grep, Glob, Bash`).
   Sauvegarde préalable : `cp -r . /tmp/agents_backup_$(date +%s)`.
   **Portée inter-projets** — c'est une correction de configuration, pas une correction de code.
2. **`.coverage`** (fichier suivi par git) a été écrasé par le run pytest du `quality-gatekeeper`,
   puis restauré par `git checkout -- .coverage`. Seule écriture dans le repo pendant l'audit.

Arbre de travail re-vérifié après coup : `git status --short` vide.

### Incidents outillage

- Trois sous-agents morts sur `API Error: 503 ... claude-sonnet-5 无可用渠道` ; relancés en `model: opus`.
- `python` absent du PATH ; usage de `python3`, tâches longues passées en arrière-plan (timeout 120 s).
- Faux positif Glob : `find tests -path "*api*"` matche `tests/domain/test_capital.py`
  (« api » contenu dans « c-**api**-tal »). Corrigé par un grep de contenu.
- `echo "exit=$?"` après un pipe mesurait le code de `head`, pas de `grep` :
  les conclusions « aucun secret » reposent sur la **sortie vide**, pas sur `exit=0`.

### Limites déclarées

- `.env` **non lu dans son contenu de valeurs**. Seuls les NOMS de clés ont été relevés.
- Le `code-review-critic` (dit ci-après « agent stubs ») a produit une conclusion fausse
  sur l'autorité du RiskEngine — voir §9. Ses autres constats ont été recroisés.
- Aucun test n'a été exécuté contre un broker réel. Aucun ordre réel n'a été envoyé.
- La couverture frontend n'a pas pu être mesurée : **aucun test frontend n'existe**.

---

## §1 — ARCHITECTURE : **NON CONFORME**

### 1.1 Convention réelle (prouvée par grep, non documentée)

`domain/` = **stdlib uniquement**. C'est la règle effectivement respectée dans le code…
à une exception près, qui est une brèche franche :

```python
# src/aegis_trade/domain/council.py:5
from aegis_trade.engine.portfolio import Portfolio
```

Utilisé en `domain/council.py:35`. Le domaine importe une couche applicative.
**Unique violation de la frontière domaine**, mais violation réelle.

### 1.2 Imports inter-couches inversés

Au-delà de `domain/council.py`, le graphe de dépendances est inversé sur cinq axes :

- `engine/` importe `agents/`
- `engine/` importe `infrastructure/`
- `core/` importe `infrastructure/`
- `infrastructure/` importe `application/`
- `infrastructure/` importe `engine/`

L'architecture hexagonale prescrit l'inverse : l'infrastructure dépend du domaine, jamais l'opposé.

### 1.3 Violation hexagonale explicite dans la stratégie ML

`application/strategy/ml_strategy.py` importe les classes **concrètes** `QlibPredictor`
et `DatasetBuilder` au lieu de ports. Seuils : `buy_threshold=0.52, sell_threshold=0.48`.
Combiné au prédicteur constant `0.55` (voir §4), cette stratégie ne peut émettre que BUY.

### 1.4 Autorité du RiskEngine : **ROMPUE SUR 4 CHEMINS**

`CLAUDE.md` : « Aucun chemin de code ne doit pouvoir router un ordre en contournant le risk check. »
Constat : quatre chemins le font.

**Signature réelle** :

```python
# src/aegis_trade/engine/global_risk.py:50-61
def validate_order(
    self,
    order: OrderEvent,
    portfolio: "Portfolio",
    latest_prices: dict[Symbol, Decimal]
) -> Tuple[bool, str]:
```

Synchrone, trois arguments positionnels obligatoires.

**Chemin 1 — appel cassé par arité (orchestrateur paper trading)** :

`application/paper_trading/orchestrator.py:132-134` appelle `validate_order` avec **deux**
arguments au lieu de trois. `TypeError` garanti à l'exécution.

**Chemin 2 — `api/routers/positions.py` : aucun risk check du tout**

Fichier de 44 lignes, lu intégralement. `risk_manager` n'y est jamais touché :

```python
# src/aegis_trade/api/routers/positions.py:43
await orchestrator.broker.submit_order(paper_order)
```

Autres défauts du même fichier :
- `:32` logique métier dans la couche API
- `:36` `asset_class="forex"` codé en dur
- `:25` `orchestrator = Depends(get_orchestrator)` non typé
- `:15` et `:19` retournent la **même expression** : `GET /api/positions/open`
  n'effectue aucun filtrage sur les positions ouvertes

**Chemin 3 — `providers/vnpy_adapter.py` : envoi direct au gateway**

`on_order_event` (`:52`, `:57`) appelle `self.send_order(event)` sans contrôle, qui atteint :

```python
# src/aegis_trade/providers/vnpy_adapter.py:79
self.main_engine.send_order(req, self.gateway_name)
```

`grep -in "risk\|validate" src/aegis_trade/providers/vnpy_adapter.py` : **aucun match**.
Aggravants : `:69` `Exchange.SMART` codé en dur (contourne `mapper.py`), `:82` retourne `"mock_id"`.

**Chemin 4 — `infrastructure/live/vnpy/execution.py` : idem**

`:14`, `:47` troisième chemin d'envoi sans contrôle. `grep "risk\|validate"` : **aucun match**.
`:46` `gateway_name = exchange  # simplification`.

### 1.5 Le seul appel correct est sous `# type: ignore`

```python
# src/aegis_trade/infrastructure/risk/global_risk_adapter.py:86
return self.risk_manager.validate_order(order_event, portfolio, latest_prices)  # type: ignore
```

Trois arguments — correct. Mais placé sous un `# type: ignore` nu, **exactement sur la frontière
d'autorité du RiskEngine**, supprimant le vérificateur qui aurait détecté le chemin 1.

Total `# type: ignore` dans `src/` : **exactement 2**, tous deux nus donc en échec `CLAUDE.md` :
1. `infrastructure/risk/global_risk_adapter.py:86`
2. `providers/mt5_provider.py:4` — `import MetaTrader5 as mt5  # type: ignore`

### 1.6 `emergency_halt` : nom indéfini au runtime

```python
# src/aegis_trade/engine/global_risk.py:29
    async def emergency_halt(self, gateway: 'IPaperBroker' = None) -> dict:
```

`IPaperBroker` n'est importé **nulle part** dans ce fichier, pas même sous `TYPE_CHECKING`.
Appelé depuis `api/routers/risk.py:19`. Triple confirmation : `architecture-guardian`,
`ruff F821` en `:29:46` (`Undefined name IPaperBroker`), et lecture directe.
Second défaut sur la même ligne : `= None` sur un paramètre annoté non-Optional
(implicit-Optional, refusé par `mypy --strict`).

Le kill switch du système est donc porté par une signature qui ne résout pas.

---

## §2 — SÉCURITÉ ET SUPPLY CHAIN : **BLOQUANT**

### 2.1 Secrets : la piste du brief est INFIRMÉE

Le brief annonçait « secrets commités (tokens Deriv notamment) ». **Faux.** Aucun secret
n'est présent, ni dans l'arbre courant, ni dans l'historique :

- `.env` n'est pas suivi : `git check-ignore -v .env` renvoie `.gitignore:9`.
- `.env` ne contient que des **NOMS de clés** : `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`,
  `MT5_TERMINAL_PATH`. Aucune valeur n'a été lue.
- Pickaxe sur **toutes** les refs pour `Deriv`, `sk-ant-`, `sk-proj-`, `sk-or-v1`,
  `*_API_KEY`, `BEGIN * KEY` : zéro occurrence.
- Les occurrences de `app_id` sont `DerivAPI(app_id=1089)` — valeur publique par défaut
  de l'API Deriv, pas un secret.
- `providers/mt5_provider.py:24-27` lit bien via `os.environ.get`.

Réserve méthodologique : cette conclusion repose sur des **sorties vides**, pas sur des
codes de retour (`echo "exit=$?"` après un pipe mesurait `head`).

### 2.2 Vulnérabilités déclarées : 0 sur 3 scanners

| Scanner | Périmètre | Résultat |
|---|---|---|
| pip-audit | 307 pins `uv.lock` | 0 |
| pip-audit | 282 pins `requirements.txt` | 0 |
| npm audit | 172 paquets frontend | 0 |

### 2.3 `mlflow==1.27.0` — cluster de vulnérabilités LATENT

`uv.lock:2820-2822` épingle `mlflow==1.27.0`, tiré transitivement par `pyqlib 0.9.7`.
Base OSV : **144 vulnérabilités, dont 21 CRITICAL et 38 HIGH** sur cette version.

Qualification honnête : **latent, pas actif**. Aucun `import mlflow` dans `src/`,
`scripts/` ou `tests/`, aucun serveur de tracking lancé. Le risque devient réel
le jour où Qlib est réellement branché (voir §6) ou si un serveur MLflow est démarré.

### 2.4 Docker : exposition réseau en root

- `deploy/docker/Dockerfile.backend:28` : `--host 0.0.0.0` — écoute sur toutes les interfaces.
- Aucune directive `USER` dans le Dockerfile : **le conteneur tourne en root**.
- `docker-compose.yml` publie `8000:8000` et `restart: unless-stopped`.
- L'installation se fait par `uv pip install -r pyproject.toml`, donc **`uv.lock` est ignoré** :
  les 307 pins audités ne sont pas ceux qui seront réellement installés en conteneur.

Combiné à §2.5 et §2.6 : une API sans authentification, sans rate limiting,
exposée sur toutes les interfaces, en root, avec des dépendances non verrouillées.

### 2.5 WebSocket : acceptation inconditionnelle et mémoire non bornée

```python
# src/aegis_trade/api/ws/manager.py:37-45
```

`accept()` est appelé sans aucune condition — pas de token, pas d'origine vérifiée.
Le champ `topic` fourni par le client est utilisé **directement comme clé de dictionnaire**
sans validation ni liste blanche : un client peut créer un nombre non borné de topics.
Croissance mémoire non bornée pilotée par un tiers non authentifié.

### 2.6 Aucun rate limiting

`grep -rn "slowapi\|limiter\|RateLimit" src/` : **aucun match**. Aucun garde-fou
sur le nombre de requêtes, y compris sur les routes POST qui déclenchent des ordres (§1.4 chemin 2).

### 2.7 CORS permissif

```python
# src/aegis_trade/api/main.py:16-19
app.add_middleware(
    ...
    allow_origins=["*"],  # Local-First architecture
    ...
    allow_credentials=True,
)
```

`allow_origins=["*"]` **combiné à** `allow_credentials=True`. Le commentaire
« Local-First architecture » ne tient pas : le conteneur écoute sur `0.0.0.0` (§2.4).

### 2.8 Divergence `requirements.txt` / `uv.lock` / `pyproject.toml`

| Problème | Constat |
|---|---|
| mlflow | `requirements.txt` : `3.14.0` — `uv.lock` : `1.27.0`. Deux mondes différents. |
| Absences de `requirements.txt` | torch, stable-baselines3, finrl, faiss-cpu, gymnasium, tenacity, einops |
| Dépendances non épinglées | `pyproject.toml:16,17,22,34-36` : `vnpy`, `pyqlib`, `ta`, `pytest*` sans version |

Conséquence : trois descriptions incompatibles de l'environnement. Le build Docker
utilise `pyproject.toml` (non épinglé), l'audit a mesuré `uv.lock`, et `requirements.txt`
décrit un troisième état. Aucune reproductibilité.

### 2.9 Provenance et obsolescence

- `sparsediffpy==0.3.0` (`uv.lock:1162`, `uv.lock:5740`) : **aucune provenance identifiable**,
  jamais importé dans le code. Paquet inconnu présent dans le lock d'un système financier.
- `gym==0.26.2` : bibliothèque dépréciée (remplacée par `gymnasium`, également présente).

### 2.10 Frontend

```typescript
// frontend/src/api/websocket.ts
```

- URL `ws://127.0.0.1:8000` **codée en dur** — pas de variable d'environnement, pas de `wss`.
- `JSON.parse` du message serveur injecté dans le store **sans validation de schéma**.
- `frontend/package.json` : toutes les dépendances en plages ouvertes (`^`),
  **aucun script `test`**, **aucun test frontend n'existe**.

---

## §3 — GATES DE QUALITÉ : **BLOQUÉ**

Aucun gate `CLAUDE.md` ne passe. Pire : deux d'entre eux ne s'exécutent même pas.

### 3.1 mypy : s'interrompt avant toute analyse

```
$ .venv/bin/mypy --strict src/
Source file found twice under different module names
Found 2 errors in 2 files (errors prevented further checking)
$ echo $?
2
```

**Aucune analyse de type n'a lieu.** Cause : 36 répertoires sans `__init__.py`,
mypy résout donc les mêmes fichiers sous deux noms de module.

Contourné manuellement avec `--explicit-package-bases --namespace-packages` :

```
Found 929 errors in 186 files (checked 219 source files)
```

**929 erreurs de typage sur 186 fichiers.** C'est le chiffre réel, jamais mesuré jusqu'ici
parce que le gate s'arrêtait avant.

### 3.2 pytest : la collecte échoue

```
$ .venv/bin/pytest -v --cov
4 errors during collection
E   ModuleNotFoundError: No module named 'src'
$ echo $?
2
```

Cause : **7 lignes d'import préfixées `src.`** dans 4 fichiers de tests RL.
La suite entière ne se collecte pas.

En contournant la collecte :

```
5 failed, 257 passed, 3 errors in 80.98s
```

Détail des 5 échecs et 3 erreurs :

| Type | Nombre | Cause |
|---|---|---|
| `Failed: async def functions are not natively supported` | 4 | `pytest-asyncio` **absent**, aucun `conftest.py` dans tout le repo, 7 `@pytest.mark.asyncio` émettent `PytestUnknownMarkWarning` |
| `AssertionError: expected call not found` | 1 | `create_order(verdict, 'AAPL', 1.0)` attendu, 2 arguments supplémentaires reçus |
| `TypeError: Can't instantiate abstract class PaperBroker` | 3 (erreurs de setup) | méthodes abstraites `cancel_all_orders`, `close_all_positions` non implémentées |

Les 4 tests `async` ne testent donc **rien** : ils ne s'exécutent pas, ils échouent
au niveau du runner. Toute la logique asynchrone (orchestrateur, gateway, WebSocket)
est de facto non testée.

Zéro `skip`, zéro `xfail` dans la suite — les tests ne masquent rien volontairement.

### 3.3 ruff : 329 violations

```
$ .venv/bin/ruff check src/ tests/ scripts/
329 errors (src 216, tests 88, scripts 25)
```

| Code | Occurrences | Signification |
|---|---|---|
| F401 | 249 | import non utilisé |
| F405 | 33 | nom possiblement non défini via `import *` |
| E402 | 19 | import hors du haut de fichier |
| F841 | 14 | variable locale assignée jamais utilisée |
| F541 | 8 | f-string sans placeholder |
| F403 | 2 | `import *` |
| E701, E712, F811, F821 | 1 chacun | — |

Le `F821` est le plus grave : `global_risk.py:29:46 Undefined name IPaperBroker` (§1.6).

### 3.4 Couverture : chiffres incomparables

| Source | Fichiers | Instructions | Couverture |
|---|---|---|---|
| `.coverage` **commité** | 13 | 257 | 68 % |
| Run de l'audit | 189 | 7172 | 73 % |

Le `.coverage` versionné provient d'un run partiel limité au Council. Les deux chiffres
ne mesurent pas la même chose : **le 68 % affiché dans le repo n'a aucune valeur**.

Modules les plus faibles (run de l'audit) :

| Module | Couverture |
|---|---|
| `providers/kronos/shiyu_model/kronos.py` | 8 % |
| `providers/kronos/trainer.py` | 16 % |
| `providers/kronos/shiyu_model/module.py` | 19 % |
| `infrastructure/live/vnpy/execution.py` | 33 % |
| `providers/kronos_adapter.py` | 45 % |
| `engine/ai_decision_engine.py` | 67 % |
| `engine/risk.py` | 71 % |
| `engine/global_risk.py` | **77 %** |
| `engine/portfolio.py` | 78 % |

Le `GlobalRiskManager` — autorité absolue selon `CLAUDE.md` — est couvert à 77 %.

### 3.5 Ratio tests / modules et zones non testées

- **87 fichiers de tests pour 219 modules** — ratio 0,40.
- **Zéro test d'API** : `grep -rln "TestClient\|api.main\|api\.routers" tests/` ne renvoie rien.
  Le chemin 2 de contournement du RiskEngine (§1.4) n'aurait jamais pu être détecté par la suite.
- Aucun test pour `engine/reasoning_events.py` ni `domain/trade_record.py`.
- `TODO/FIXME/XXX/HACK` dans `src/` : **0**. Le code ne signale pas sa propre dette —
  c'est précisément ce qui rend les stubs du §4 dangereux : rien ne les marque comme provisoires.
- `NotImplementedError` dans `src/` : 4 (tous dans `openbb_provider.py`).

### 3.6 Cause racine commune : paquets namespace cassés

**Exactement 36 répertoires sans `__init__.py`** — tous les sous-paquets de premier niveau
sauf `domain`, `engine`, `core`, `utils`, `dataset`.
**Exactement 7 lignes d'import préfixées `src.`** dans 4 fichiers de tests RL.

Ces deux défauts, à eux seuls, neutralisent simultanément mypy **et** pytest.
C'est pourquoi le Lot 0 du plan de correction les traite en premier : tant qu'ils
existent, aucune mesure de qualité n'est possible, donc aucune correction n'est vérifiable.

Seul gate qui passe : `import aegis_trade` fonctionne.

---

## §4 — REVUE DE CODE ET STUBS : le cœur du problème

Le système n'est pas « incomplet ». Il est **complet en apparence et creux en fonction**.
Trois anti-patterns récurrents, chacun conçu pour ne produire aucune erreur visible :

1. `try/except ImportError` sur une dépendance tierce, avec repli sur `None` et `return True`.
2. Une classe nommée `...Mock` renvoyant une constante, câblée en production.
3. Un composant correct… sans aucun site d'appel.

### 4.1 `DerivGateway` — broker simulé de bout en bout

`infrastructure/paper/deriv_gateway.py` :

```python
# :68-71
except ImportError:
    ...
    self.api = None
    return True
```

L'échec d'import de l'API Deriv renvoie **succès**. Puis :

```python
# :87
fill_price = Decimal("100.0")  # fallback stub
# :88
latency_ms = 50.0  # fallback stub
```

Tout le bloc d'appel réel à l'API est **commenté**. Autres constats :
- `:128` `risk_decision="APPROVED"` codé en dur dans l'événement de fill.
- `:136-139` `cancel_order` : corps commenté, `pass` nu, `return True`.
- **Aucune méthode de souscription** : zéro `subscribe`, zéro `tick`, zéro `quote`.
  Aucun fichier `DerivMarketGateway` n'existe. **Le système ne reçoit aucun prix réel.**
- `:183` `LiveDerivGateway` **hérite** de `DerivGateway` — donc la passerelle « argent réel »
  hérite des mêmes stubs, et vit dans le paquet `paper/`.

C'est le point le plus grave du §4 : le gateway « live » remplit à 100,00 en dur.

### 4.2 Orchestrateur paper trading — placeholders et exception mortelle

`application/paper_trading/orchestrator.py` :

```python
# :71-97, sous le commentaire :
# 1. Build MarketContext (MVP placeholders for now until FeatureExtractor is built)
features={"trend_score": 0.5, ..., "rsi": 55.0, "ema_distance": 0.1, "atr": 1.5}
```

`:97` l'état RL est `np.zeros(30)`.

**L'exception meurt en silence.** `:50-51` :

```python
self._market_feed_task = asyncio.create_task(self._process_feed())
self._monitoring_task = asyncio.create_task(self._monitor_portfolio_loop())
```

Dans `_process_feed` (`:61`), le `try:` est en `:95` et le `except Exception as e:` en `:113`,
tous deux à l'indentation 16. L'appel `:132 is_approved, reason = self.risk_manager.validate_order(`
est à l'indentation 12 : **il est hors du seul gestionnaire d'exception**.

Conséquence en chaîne : `TypeError` d'arité (§1.4 chemin 1) → exception non capturée →
la tâche `asyncio` meurt → **aucun log, aucune alerte, la boucle de trading s'arrête sans bruit**.

Autres constats du même fichier :
- `:154-156` `process_signal` marqué déprécié mais toujours présent.
- `:169-184` `_monitor_portfolio_loop` : `:172 equity=balance  # Simplified`, `:173 drawdown=0.0`,
  `:174-179` expositions / marge / PnL à zéro, `:184 _ = snapshot` — **l'objet est jeté**.
  Le drawdown qui alimente le kill switch (`global_risk.py:84`) vaut donc structurellement 0.

### 4.3 Le Council est câblé mais inerte — prouvé par exécution

Clés de features réellement lues par les agents :

| Agent | Clé attendue |
|---|---|
| `liquidity_agent.py:13,14` | `spread`, `volume` |
| `momentum_agent.py:13` | `rsi` |
| `trend_agent.py:23` | `ema_50` |
| `execution_agent.py:13` | `broker_latency_ms` |
| `volatility_agent.py:14,15` | `bb_upper`, `bb_lower` |

Placeholders fournis par l'orchestrateur : `trend_score`, `rsi`, `ema_distance`, `atr`.
**Seul `rsi` correspond.** Exécution réelle du Council avec ce contexte :

```
7 agents : WAIT conf=0.0
MomentumAgent : WAIT conf=0.1
VERDICT: WAIT | mult=0.0 | conf=0.0
create_order(...) -> None
```

Le Council à 8 agents ne peut mathématiquement produire autre chose que `WAIT`.
**Aucun ordre ne peut naître du système en l'état.**

### 4.4 Le test qui masque le bug d'arité

`tests/application/paper_trading/test_orchestrator_council_integration.py:30-50` :

```python
 # Mocks
 broker = MagicMock(spec=IPaperBroker)
 broker.submit_order = AsyncMock()
 ...
 risk_manager = MagicMock(spec=GlobalRiskManager)
 risk_manager.validate_order.return_value = (True, "OK")
```

`MagicMock(spec=X)` vérifie l'**existence** de l'attribut, **pas la signature**.
Les lignes `:39-40` acceptent donc un appel à deux arguments là où le vrai code en exige trois.
Le test passe au vert sur un code qui lève `TypeError` en production.

C'est le mécanisme exact par lequel « les tests passent » a coexisté avec un système cassé.

### 4.5 Qlib : façade complète

- `providers/qlib/model_factory.py:17-35` : `class LightGBMModelMock(IModel)` renvoyant `[0.55 ...]`.
- `providers/qlib/trainer.py:38` : `"mock_loss": 0.05`.
- `providers/qlib/bootstrap.py:17-18` : l'enregistrement est **commenté**.
- **`import qlib` n'apparaît nulle part dans `src/`.**

Combiné à `ml_strategy.py` (`buy_threshold=0.52`, §1.3) : le prédicteur renvoie toujours 0,55,
donc la stratégie ML est un générateur de BUY constant.

### 4.6 Validateurs : `passed=True` codé en dur

| Fichier | Lignes | Constat |
|---|---|---|
| `hold_out_validator.py` | `:42-48` | `# Stub result pour l'architecture` ; construit un `Backtester` en `:32` et **ne l'exécute jamais** |
| `walk_forward_validator.py` | `:21-26` | `passed=True` constant |
| `monte_carlo_validator.py` | `:22-27` | `passed=True` constant |
| `benchmark_validator.py` | `:21-26` | `passed=True` constant |
| `multi_validators.py` | `:21-26`, `:37-42` | `passed=True` constant |

Traçabilité falsifiée : `validation_runner.py:57 git_version="v1.0.0-mock"`,
`:60 data_hash="hash_mock_1234"`.

**C'est la violation la plus grave du pipeline `CLAUDE.md`** : les six validateurs qui doivent
prononcer GO/NO-GO renvoient GO sans rien calculer, et signent le résultat avec un faux hash.
Un validateur absent bloque ; un validateur qui ment laisse passer.

### 4.7 Télémétrie du dashboard partiellement fabriquée

`application/monitoring/engine.py:60-78` :

```python
cpu_usage=0.0
BrokerSnapshot(connected=True, latency_ms=12.5, gateway="BINANCE")
StrategySnapshot(id="alpha_momentum_v1", status="Live", running_time="14h 22m")
```

`gateway="BINANCE"` alors que le broker réellement câblé est **Deriv** (`api/deps.py:43-45`).
`status="Live"`, `running_time="14h 22m"` : chaînes constantes.

Ce qui est **authentique** dans ce fichier : le PnL (`:126`, `:129`, `:143-144`, `:178`, `:204`)
et les features issues de `pos.opening_context` (`:181-195`).
Autres défauts : `:18 import random` mort, `:87-89` exceptions avalées,
`:91-165 process_event` de 75 lignes avec `ev` réannoté en `:97` et `:105`.

Un opérateur regardant ce dashboard voit « Live / connecté / 12.5 ms / BINANCE » sur un système
qui ne reçoit aucun prix. **C'est un faux signal de bon fonctionnement.**

### 4.8 Le runner de production ne démarre pas

`scripts/run_live_paper_trading.py` (77 lignes) :

- `:10-12` importe `application.council.{aggregator,resolver,council}` —
  ces modules **n'existent pas** (réels : `vote_aggregator.py`, `conflict_resolver.py`, `orchestrator.py`).
- `:9` importe `Portfolio` (réel : `PortfolioEngine`).
- `:44-47`, `:49` : kwargs erronés.
- `:63-68` : `await asyncio.sleep(1)  # Keep alive`.

Vérifié par exécution :

```
ModuleNotFoundError: No module named 'aegis_trade.application.council.aggregator'
```

Le point d'entrée censé lancer le trading meurt **à l'import**.

### 4.9 Kronos : structure réelle, données aléatoires

- `kronos_adapter.py:63-71` prédit sur `np.random.randn(512,6)+100`.
- `kronos_adapter.py:40-41` : le `data_provider` est stocké et **jamais lu**.
- `kronos/trainer.py` (117 l., `class KronosFineTuner`) et `dataset_builder.py` (110 l.) sont réels,
  exercés par `scripts/run_kronos_smoke_test.py:12-14`.
- `kronos/model_factory.py:14-15` → `NeoQuasar/Kronos-*` (à ne pas confondre avec `amazon/chronos-t5-mini`).
- `api/deps.py:65,69` : `TrendAgent()` / `PatternAgent()` reçoivent **aucun forecaster** →
  la branche Kronos est morte en production.

### 4.10 Duplications : souveraineté numérique perdue

Un système de trading doit avoir **une seule définition** de chaque quantité. Ici, non :

| Quantité | Implémentations | Localisation |
|---|---|---|
| Indicateurs techniques / ATR | **4 impl., 3 ATR divergents** | `utils/math.py:66-135`, `engine/strategy.py:118-145`, `application/reflection/extractor.py:54-101`, `infrastructure/features/technical_extractor.py:100-140` |
| PnL réalisé | 3 | `engine/portfolio.py:92-93`, `engine/backtester.py:180-188`, `application/monitoring/engine.py:126-129` |
| Equity | 2 formules | `engine/portfolio.py:165` vs `application/monitoring/engine.py:100` |
| Annualisation | 2 | `engine/portfolio.py:227` vs `engine/performance.py:70,74` |
| Verdict → Order | 2 convertisseurs | `application/council/orchestrator.py:72-91` vs `application/validation/council_adapter.py:82-95` |
| `DatasetBuilder` | 2 classes | `providers/qlib/dataset_builder.py:26`, `dataset/builder.py:8` |

Conséquence directe et mesurable : l'equity affichée au dashboard peut différer de l'equity
sur laquelle le drawdown est calculé (`engine/global_risk.py:84`). **Le kill switch et l'écran
de contrôle ne parlent pas de la même somme d'argent.**

La loi `CLAUDE.md` « Qlib ne calcule jamais d'indicateurs » est respectée en lettre —
mais la souveraineté mathématique du `FeatureEngine` est violée par ces 4 implémentations.

### 4.11 Restriction OpenBB

```python
# providers/openbb_provider.py:43
raise DataProviderError(f"Mission C restricts OpenBBDataProvider to DXY and US10Y exclusively. Requested: {symbol.name}")
```

Plus `NotImplementedError` en `:100`, `:103`, `:106`. Le provider est **réel** mais
verrouillé sur deux symboles macro par une contrainte de mission ancienne.

---

## §5 — DOCUMENTATION ET INTÉGRITÉ GIT

### 5.1 L'historique git : 60,5 % de messages de refus

**23 commits sur 38 (60,5 %) portent un message de refus de LLM** au lieu d'un message de commit :

```
72d2c4e, 47327e5, 71acc20, ce1d4b9, 652d0b2, b39270d, 6855e32, 6dfe8cb,
5af086f, 731e58d, 813db16, 4aa9b3b, ea81b51, 4f22ec6, 8202ac4, 2fbba48,
9cf9c27, 19b72b3, 6434369, b5b73ff, 84ff7b7, c984896, 4df5ae8
```

Circonstance aggravante : `72d2c4e` — un message de refus — **supprime**
`providers/kronos/predictor.py` et `tests/providers/test_kronos_predictor_ensemble.py`.
Une suppression de code et de test documentée par une excuse.

L'historique est donc inexploitable pour un `git bisect` ou une revue de régression.

### 5.2 Hygiène du dépôt

- `.coverage` (53 248 octets, base SQLite) **versionné** — artefact de build dans git.
- `src/aegis_trade.egg-info/*` **versionné** — idem.
- `models/` n'est **ni suivi ni ignoré** : état indéterminé.
- Dernière ligne de `.gitignore` : `r e f e r e n c e /` — espaces intercalés, **règle inopérante**.
- `providers/__pycache__/` mélange des bytecodes `cpython-311` et `cpython-313` :
  deux interpréteurs ont tourné sur ce code.

### 5.3 Gouvernance ADR : deux numérotations concurrentes

- `docs/ADR/` : `0001` à `0016`
- `docs/architecture/adr/` : `ADR-001` à `ADR-003`

Aucun lien entre les deux ensembles. Aucun ADR n'existe pour trois décisions structurelles
déjà prises dans le code :

1. Le **vendoring de Kronos** dans `src/aegis_trade/providers/kronos/shiyu_model/`
   (1 532 lignes de code tiers versionnées, **aucun fichier LICENSE dans le repo** — voir §2 et §10).
2. L'adoption de **stable_baselines3 / RL**.
3. La création de la frontière `infrastructure/live/vnpy/`, qui duplique `providers/vnpy_adapter.py`.

`ADR-002:8,9` mentionne FinGPT et n'est pas marqué `Superseded` alors que la décision est invalidée.

### 5.4 Documentation en contradiction avec le code

Toutes les lignes ci-dessous sont fausses au regard du code mesuré.

**`docs/phase2/PHASE2_ROADMAP.md`**

| Ligne | Affirmation | Réalité mesurée |
|---|---|---|
| `:3` | désigne `VALIDATION_PIPELINE_REPORT.md` comme vérité GO/NO-GO | ce rapport est lui-même faux (`:16`) |
| `:13` | `[x] VALIDATED` AI-01 Memory Engine | `grep "MemoryManager(" src/ scripts/` → **0** |
| `:16` | `[CODE-READY]` AI-02 | `ReflectionPipeline(` → **0** |
| `:22-23` | AI-04 RL livré | `PolicyEvaluator(|PolicyTrainer(|ValidationRunner(` → **0** |
| `:28-30` | AI-08 `[PAUSED]` | justification obsolète (voir §8) |
| `:29` | Kronos injecté dans Trend/Pattern | `api/deps.py:65,69` ne passe aucun forecaster |
| `:45,49,53` | `[CODE-READY]` | 6 validateurs à métriques littérales (§4.6) |

**`docs/phase2/PHASE2_BACKLOG.md`**

| Ligne | Affirmation | Réalité mesurée |
|---|---|---|
| `:11` | `OllamaReasoner` fait | jamais instancié ; production utilise `MockReasoner()` (`api/deps.py:53`) |
| `:16` | `[AI-05-B]` GlobalRiskManager Veto | `grep "knowledge\|veto" engine/global_risk.py` → **0** |
| `:21` | BenchmarkGate fait | seuls consommateurs : 3 lignes de tests |

**`docs/phase2/VALIDATION_PIPELINE_REPORT.md`**

| Ligne | Affirmation | Réalité mesurée |
|---|---|---|
| `:16` | seuils `Win Rate >= 0.55`, `Sortino >= 1.2` | `benchmark_gate.py:14-15` : `min_win_rate=0.85`, `min_sortino=2.0` |
| `:38` | `Verdict: NO-GO` | **exact** — seule ligne conforme du fichier |

**`docs/phase2/DEPENDENCY_MATRIX.md`** (colonnes `:3` = `Repo / Package | Statut | Valeur | Fichiers d'implémentation réels | Modules utilisés`
— ce fichier ne contient **aucun pourcentage d'intégration**)

| Ligne | Affirmation | Réalité mesurée |
|---|---|---|
| `:5` | python-deriv-api « Intégré » | non prouvé ; token `"dummy"` (`api/deps.py:40`) |
| `:8` | Qlib « Intégré » | `bootstrap.py:17-18` commenté ; aucun `import qlib` dans `src/` |
| `:9` | stable_baselines3 | sur-déclaré au regard de l'usage réel |
| `:10` | Kronos « Reporté / N/A (Matériel insuffisant) / modules Aucun » | 1 532 lignes versionnées, adaptateur + trainer + dataset builder |
| `:13` | TradingAgents abandonné | contredit `PROJECT_PHILOSOPHY.md:16` |
| — | **vn.py absent de la matrice** | 2 implémentations dans le code |

**`docs/phase2/GITHUB_INTEGRATION_GUIDE.md:148-149`** — FinGPT : infirmé.

**Hors `phase2/`**

| Fichier:ligne | Réalité mesurée |
|---|---|
| `docs/SYSTEM_ARCHITECTURE.md:79` | obsolète |
| `README.md:107-117` | liste 9 sous-paquets ; le code en a 12. `application/` et `api/` absents alors qu'ils totalisent 78 fichiers |
| `docs/PAPER_TRADING_ARCHITECTURE.md:4` | obsolète |
| `PROJECT_PHILOSOPHY.md:10` | vn.py « système nerveux » — non |
| `PROJECT_PHILOSOPHY.md:14` | ChromaDB — `grep -rin "chroma" src/` → **0** |
| `PROJECT_PHILOSOPHY.md:15` | FinGPT — abandonné |
| `PROJECT_PHILOSOPHY.md:16` | TradingAgents comme orchestration du council — c'est une inspiration architecturale, pas une dépendance |
| `ADR-002:8,9` | FinGPT ; décision invalidée, pas marquée `Superseded` |
| `AGENTS_SPECIFICATION.md:35` | obsolète |
| `ENGINEERING_RULES.md:11` | obsolète |
| `PROVIDERS_ROADMAP.md:52-53` | obsolète |
| `RESEARCH_LOGBOOK.md:37` | « ~917 MB » contre « <300MB RAM » dans la roadmap — contradiction interne |

`BENCHMARKS.md` : 9 seuils conformes exactement au code. Non couverts par le gate :
Trades/day, Spread Cumulé, Vector DB Query Time, Avg Win/Avg Loss.

---

## §6 — ÉTAPE 2 : QUELLES SOURCES GITHUB SONT RÉELLEMENT INTÉGRÉES

Verdict établi par `grep` sur `src/`, `scripts/`, `tests/` — pas sur la documentation.

| Source | Verdict | Preuve |
|---|---|---|
| **OpenBB** | **RÉEL mais bridé** | `openbb_provider.py:43` lève sur tout symbole hors DXY / US10Y ; `NotImplementedError` `:100,103,106` |
| **Qlib** | **FAÇADE** | aucun `import qlib` dans `src/` ; `bootstrap.py:17-18` commenté ; `model_factory.py:17-35 class LightGBMModelMock` |
| **vn.py** | **RÉEL mais dupliqué** | `providers/vnpy_adapter.py` + `infrastructure/live/vnpy/execution.py` ; absent de `DEPENDENCY_MATRIX.md` |
| **Stable-Baselines3** | **RÉEL** | dépendance installée et importée |
| **FinRL** | **ABSENT** | présent en docstring uniquement |
| **Kronos** | **STRUCTURELLEMENT COMPLET, FONCTIONNELLEMENT VIDE** | `kronos_adapter.py:63-71` prédit sur `np.random.randn(512,6)+100` ; vendoré sans LICENSE |
| **FinGPT** | **ABANDONNÉ** (décision saine) | contredit par 6 lignes de doc (§5.4) |
| **TradingAgents / AutoHedge** | **inspiration architecturale, par décision explicite** | pas un manque ; seule l'incohérence documentaire est relevée |
| **lightweight-charts** | **RÉEL** | frontend |

---

## §7 — ÉTAPE 3 : LA CHAÎNE DE BOUT EN BOUT

**Elle ne fonctionne jamais de bout en bout.** Le seul segment authentique est le calcul de PnL
(`engine/portfolio.py`), et il est alimenté par des prix constants.

| Maillon | État | Preuve |
|---|---|---|
| Données entrantes | **absent** | aucun `DerivMarketGateway`, aucun subscribe/tick/quote dans `providers/deriv/` |
| Features | **placeholders** | `orchestrator.py` : `trend_score=0.5, rsi=55.0, ema_distance=0.1, atr=1.5` ; seul `rsi` correspond à une clé attendue par un agent |
| Council | **câblé mais inerte** | exécution réelle : `7 agents WAIT conf=0.0`, `VERDICT: WAIT | mult=0.0 | conf=0.0` |
| Ordre + risk check | **doublement cassé** | `orchestrator.py:132-134` passe 2 args à une signature à 3 → `TypeError` ; l'appel est hors du `try/except` (§4.2) |
| Fills | **constants** | `deriv gateway :87 fill_price = Decimal("100.0") # fallback stub` |
| Snapshot portefeuille | **simulé puis jeté** | `:172 equity=balance # Simplified`, `:173 drawdown=0.0`, `:184 _ = snapshot` |
| Knowledge Base | **factice en production** | `api/deps.py:53 MockReasoner()` |
| RL | **entrée nulle** | `orchestrator.py:97 np.zeros(30)` |
| Runner | **mort à l'import** | `ModuleNotFoundError: No module named 'aegis_trade.application.council.aggregator'` |

Conséquence directe : le drawdown qui alimente le kill switch (`global_risk.py:84`) vaut
**structurellement 0**. Le kill switch ne peut pas se déclencher.

---

## §8 — LES CINQ PISTES DU BRIEF, VÉRIFIÉES

| # | Piste du brief | Verdict | Preuve |
|---|---|---|---|
| 1 | `run_live_paper_trading.py` non fonctionnel | **CONFIRMÉ** | mort à l'import (§4.8) |
| 2 | Pas d'abonnement au prix live | **CONFIRMÉ** | aucun subscribe/tick/quote (§4.1) |
| 3 | AI-08 en pause sur justification obsolète | **CONFIRMÉ** | voir ci-dessous |
| 4 | « Façade sans données réelles » | **NUANCÉ** | triage complet en §6 : OpenBB et vn.py sont réels, Qlib est une façade |
| 5 | `InMemoryKnowledgeRepository` mal câblé | **NUANCÉ** | câblage correct, mais `MockReasoner()` en production |
| — | **secrets commités (tokens Deriv)** | **INFIRMÉ** | voir §2.1 — aucun secret nulle part |

**Piste 3, obsolète sur trois points :**

1. Confusion `amazon/chronos-t5-mini` / `NeoQuasar/Kronos-mini` — ce ne sont pas le même modèle.
2. Le fine-tuning est présenté comme à faire ; `providers/kronos/trainer.py` (117 l., `class KronosFineTuner`) existe déjà.
3. La contrainte « <300MB RAM » est contredite par la mesure `~917 MB` consignée dans
   `RESEARCH_LOGBOOK.md:37` — la justification de la pause n'a jamais été mise à jour.

**Piste 5, détail :** `pattern_agent.py:2` importe le port depuis `infrastructure/` alors que
`domain/reasoning.py:125` le déclare ; `pattern_agent.py:13` utilise un Optional implicite.

---

## §9 — CONTRADICTION ENTRE SOUS-AGENTS (déclarée, non masquée)

Le sous-agent `a4775f92e52b78be9` a conclu : « autorité du RiskEngine intacte, aucun contournement ».
**Cette conclusion est fausse.** Il n'avait examiné qu'`orchestrator.py:132`, qu'il a traité comme
« l'unique chemin d'exécution ».

Trois sources concordantes l'infirment : l'agent architecture, l'agent sécurité, et des lectures
et `grep` directs. Les 4 chemins non contrôlés sont documentés en §1.4.

Ce point est écrit ici volontairement : **c'est exactement ce type de rapport rassurant qui a produit
l'état actuel du dépôt.** Un audit qui ne déclare pas ses contradictions internes n'est pas un audit.

Coquille de ce rapport d'agent à ne pas propager : il écrit `MododuleNotFoundError` ;
le nom réel est `ModuleNotFoundError`.

---

## §10 — 21 BLOQUANTS PRIORISÉS

**P0 — sécurité du capital. Aucune exécution, même en démo, tant que ces 6 points tiennent.**

| # | Bloquant | Preuve |
|---|---|---|
| 1 | 4 chemins d'ordre contournent le RiskEngine | §1.4 |
| 2 | `orchestrator.py:132-134` appelle `validate_order` avec 2 args sur 3 requis → `TypeError` garanti | `global_risk.py:50-61` |
| 3 | Cet appel est **hors** du `try/except` d'une tâche `asyncio.create_task` → mort silencieuse | `orchestrator.py:50-51,95,113,132` |
| 4 | `emergency_halt` porte un type non résolu : `F821 Undefined name IPaperBroker` | `global_risk.py:29` ; appelé par `api/routers/risk.py:19` |
| 5 | Le seul test qui couvre la zone masque le bug via `MagicMock(spec=…)` | `test_orchestrator_council_integration.py:30-50` |
| 6 | API exposée sans authentification : CORS `allow_origins=["*"]` + `allow_credentials=True`, WebSocket `accept()` inconditionnel, aucun rate limiting, Docker `--host 0.0.0.0` en root | `api/main.py:16-19` ; `api/ws/manager.py:37-45` ; `Dockerfile.backend:28` |

**P1 — le projet n'est pas mesurable. Rien ne peut être prouvé tant que ces 5 points tiennent.**

| # | Bloquant | Preuve |
|---|---|---|
| 7 | `mypy --strict` **n'analyse rien** : exit 2, `Source file found twice under different module names` | §3.1 |
| 8 | `LiveDerivGateway(token=token, i_understand_this_is_real_money=True)` — consentement codé en dur | `api/deps.py:43` |
| 9 | `pytest` **n'assemble pas la suite** : exit 2, 4 erreurs de collection, `No module named 'src'` | §3.2 |
| 10 | Cause racine commune : 36 répertoires sans `__init__.py` + 7 imports préfixés `src.` | §3.6 |
| 11 | **Zéro test d'API** ; ratio 87 tests / 219 modules = 0,40 | §3.5 |

**P2 — le pipeline scientifique est falsifié. Aucun modèle ne doit être branché avant.**

| # | Bloquant | Preuve |
|---|---|---|
| 12 | 6 validateurs renvoient `passed=True` codé en dur ; `hold_out_validator.py:32` construit un `Backtester` et ne l'exécute jamais | §4.6 |
| 13 | Traçabilité falsifiée : `git_version="v1.0.0-mock"`, `data_hash="hash_mock_1234"` | `validation_runner.py:57,60` |
| 14 | Qlib est une façade : `class LightGBMModelMock` renvoie `[0.55 ...]`, `"mock_loss": 0.05` | §4.5 |
| 15 | Aucune donnée de marché réelle n'entre dans le système ; le runner est mort à l'import | §7, §4.8 |

**P3 — dette structurelle et intégrité.**

| # | Bloquant | Preuve |
|---|---|---|
| 16 | 4 implémentations d'indicateurs / 3 ATR divergents / 3 PnL réalisé / 2 equity / 2 annualisations | §4.10 |
| 17 | Kronos vendoré (1 532 l.) **sans LICENSE** dans le dépôt | §5.3 |
| 18 | `mlflow 1.27.0` figé transitivement — 144 vulnérabilités OSV dont 21 CRITICAL (latent) | §2.3 |
| 19 | `Dockerfile.backend` ignore `uv.lock` (`uv pip install -r pyproject.toml`) et tourne en root | §2.4 |
| 20 | 23 commits sur 38 portent un message de refus de LLM ; `72d2c4e` supprime du code et un test | §5.1 |
| 21 | Documentation en contradiction avec le code sur ~30 lignes réparties dans 15 fichiers | §5.4 |

---

## §11 — CONCLUSION

**Verdict : NO-GO.** Le système ne fonctionne pas de bout en bout. Aucune couche n'est validée
au sens du pipeline `CLAUDE.md`.

Ce qui est réellement acquis et mérite d'être conservé :

- L'ossature hexagonale est lisible ; `domain/` est pur à **une** violation près (`domain/council.py:5`).
- Le calcul de PnL de `engine/portfolio.py` est authentique.
- Le Council à 8 agents, `VoteAggregator`, `ConflictResolver` sont réellement implémentés et câblés —
  ils sont inertes par défaut de features, pas par défaut de conception.
- OpenBB, vn.py, Stable-Baselines3 sont des intégrations réelles.
- L'abandon de FinGPT et le choix de TradingAgents/AutoHedge comme inspiration architecturale
  sont des décisions saines ; seule la documentation ne les a pas suivies.
- Aucun secret n'est commité. La piste la plus alarmante du brief est infirmée.

Ce qui est le vrai problème, et qui n'est pas un problème de code :

> Le système est **complet en apparence et creux en fonction**. Chaque couche possède un composant
> qui rend un résultat plausible sans faire le travail : `LightGBMModelMock` renvoie `0.55`,
> les validateurs renvoient `passed=True`, le gateway renvoie `fill_price=100.0` et
> `risk_decision="APPROVED"`, le snapshot renvoie `drawdown=0.0`. Aucun de ces retours n'échoue.
> Le système ne signale donc jamais qu'il ne fonctionne pas.

C'est cette propriété — l'absence d'échec bruyant — qui doit être corrigée en premier, avant
toute fonctionnalité. Un `NotImplementedError` est supérieur à un `passed=True` codé en dur.

Rien n'a été corrigé. Aucun fichier source n'a été modifié pendant cet audit
(voir §0 pour les deux seules écritures, hors code projet, et leur restauration).
