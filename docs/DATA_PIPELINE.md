# Data Pipeline Institutionnel

## Architecture
Le Data Pipeline d'Aegis Quant OS est construit selon les principes de la **Clean Architecture** et du **Domain-Driven Design (DDD)**.
Il sépare strictement le domaine métier des implémentations techniques (comme OpenBB, Qlib ou Yahoo Finance).

### Flux de Données
`Provider` -> `Validator` -> `Normalizer` -> `Cache` -> `Pipeline`

1. **Provider** : Implémente l'interface `IDataProvider`. Convertit les requêtes en appels API et utilise un `Mapper` pour renvoyer exclusivement des objets du domaine (`MarketBar`, `EconomicIndicator`, etc.).
2. **Validator** : Vérifie l'intégrité temporelle et logique des données (pas de doublons, ordre strict). Lève une `ValidationError` si nécessaire.
3. **Normalizer** : Unifie la précision numérique (ex: 8 décimales) et s'assure de l'uniformité avant mise en cache.
4. **Cache** : Abstraction (`CacheBackend`) actuellement implémentée via `MemoryCache`. Permet d'éviter de requêter les APIs distantes pour les mêmes intervalles.
5. **Pipeline** : Orchestrateur (`MarketDataPipeline`) qui coordonne l'ingestion et enrichit le résultat avec un `DataContext` (métadonnées : provider, latence, source, etc.).

## Gestion des Erreurs
Le pipeline utilise des exceptions métiers définies dans `aegis_trade.domain.exceptions.data` :
- `DataProviderError` : Erreur liée au fournisseur de données (timeout, limites d'API).
- `ValidationError` : Incohérence dans les données récupérées.
- `NormalizationError` : Échec lors du formatage des données.
- `CacheError` : Erreur lors de l'accès ou l'écriture dans le cache.
- `PipelineError` : Erreur globale lors de l'exécution du flux.

## Extensibilité
Pour ajouter un nouveau fournisseur (ex: Binance) :
1. Créer une classe implémentant `IDataProvider`.
2. L'enregistrer via `ProviderRegistry.register("binance", BinanceDataProvider)`.
3. Le pipeline pourra l'utiliser de manière transparente en passant `provider_name="binance"`.
