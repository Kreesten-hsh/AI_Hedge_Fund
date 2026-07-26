# MISSION DATA-01R : REVUE DU CACHE (CACHE REVIEW)

## 1. Stratégie de Hash (Clé)
**Statut** : ✅ **Adéquate mais perfectible**
- L'utilisation de `json.dumps` avec les kwargs triés et hashés en `MD5` permet d'obtenir des clés déterministes.
- **Risque** : `json.dumps` peut échouer si des objets complexes (comme un enum `TimeFrame.D1` au lieu de sa valeur `.value`) sont passés sans être convertis en strings au préalable. Actuellement, la conversion `str(v)` masque ce risque, mais empêche une sérialisation stricte. 

## 2. Invalidation et TTL
**Statut** : ❌ **Manquant**
- `MemoryCache` possède un paramètre `ttl` dans sa méthode `set`, mais ne le stocke pas ni ne l'exploite lors du `get()`.
- Il n'y a aucune stratégie d'invalidation (LRU / FIFO) ni de méthode `clear()` ou `invalidate(key)`. En environnement de longue durée (Live Trading), cela causera une fuite de mémoire (Out Of Memory).

## 3. Thread Safety (Concurrence)
**Statut** : ❌ **Non Thread-Safe**
- `self._cache` est un dictionnaire Python standard.
- En cas de requêtes asynchrones simultanées ou de multi-threading (ex: Council AI qui demande plusieurs actifs en parallèle), cela peut provoquer des race conditions lors des lectures/écritures. Un `threading.Lock` est impératif pour un cache mémoire institutionnel.

## 4. Extensibilité (Redis / DiskCache)
**Statut** : ⚠️ **Partielle**
- L'interface `CacheBackend` est bien conçue (`get` et `set`).
- Il manque l'obligation contractuelle (dans `CacheBackend`) d'implémenter l'effacement (`delete`) ou de gérer proprement le TTL. Pour un RedisCache, le TTL est géré nativement, mais l'interface doit le standardiser.

## Conclusion de l'Audit Cache
Le cache actuel est fonctionnel pour un script unique ("toy project"), mais totalement inadapté à un Operating System nécessitant de la concurrence et tournant 24/7. L'implémentation `MemoryCache` doit être réécrite pour inclure Thread Safety, TTL enforcement, et l'interface abstraite doit être enrichie.
