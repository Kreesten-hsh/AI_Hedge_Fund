# ADR 0015: Dashboard as Control Center

## Status
Accepted

## Context
Aegis Quant OS orchestre simultanément de la data, de l'IA, du risque et de l'exécution. En cas de tempête sur les marchés (flash crash), s'appuyer uniquement sur une interface terminal (CLI) ou des scripts Python pour comprendre ce que fait le système et l'arrêter est trop lent et source d'erreurs humaines.

## Decision
Le **Dashboard Local** est défini comme le Centre de Contrôle exclusif (Control Center).

## Rationale
- Il consolide l'état du système à la seconde près.
- Il permet une intervention humaine manuelle rapide, décisive et non sujette aux erreurs de frappe (ex: Bouton d'urgence "Flatten Positions" en un clic).
- Il affiche en clair les justifications de l'IA pour auditer immédiatement toute prise de décision suspecte.

## Consequences
- L'OS ne doit pas être exploité en mode "boîte noire" silencieuse (cron job aveugle sans interface de supervision).
- Le Dashboard doit prioritairement exposer les métriques de Risque et le statut de l'infrastructure avant même le PnL.
