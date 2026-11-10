# E08 — Dashboard et reporting

Phase de chaque tâche : **P08**. Version : **MVP**. Gate : P07 vérifiée et accord ; définitions D08 approuvées avant agrégats.

## FEA24 — Mesures définies et reproductibles

### US24 — Comme owner, je veux comprendre la valeur exacte des indicateurs de mon portefeuille.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T083 — Contrat des indicateurs | Valider définitions occupation, brut, ADR, RevPAR et encaissements | reporting | P0 | T082, T055 | Exemple chiffré approuvé, nuitées/périodes/taxes/frais/monnaies et dénominateur nul documentés | Calcul manuel confronté à fixtures : nuit adjacente, remise et remboursement | 3 |
| T084 — Dataset et projections historiques | Exploiter nuits/prix figés et périodes actives d'unités | reporting/database | P0 | T083, T035, T055 | Archivage ou nouveau tarif ne réécrit pas l'historique ; maintenance déduite | Fixtures unités ouvertes/archivées, séjour à cheval période, DST | 5 |
| T085 — Agrégats métier | Calculer réservations par statut, occupation, revenus, ADR et RevPAR | reporting | P0 | T084 | Résultats par devise, périodes locales, requêtes tenant indexées | Comparaison oracle chiffré, zéro capacité, plusieurs fuseaux/devises, annulations | 5 |

## FEA25 — Filtres et export

### US25 — Comme gestionnaire, je veux filtrer et exporter seulement les données que je peux consulter.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T086 — API overview et filtres | Exposer dates/propriété/unité avec limites | reporting/api | P1 | T085, T030 | Filtres combinables, ressource étrangère invisible, période bornée | API A/B, filtres croisés, range invalide et pagination applicable | 3 |
| T087 — Export CSV sûr | Exporter mêmes définitions avec colonnes et devise explicites | reporting | P0 | T086 | RBAC/tenant identiques, volume borné, échappement et neutralisation formules tableur | Cellules `=`, `+`, `-`, `@`, séparateurs/Unicode, période et A/B | 3 |
| T088 — Traçabilité des exports | Tracer téléchargement et nettoyage des artefacts éventuels | reporting/audit | P1 | T087, T029 | Audit minimal, aucun fichier public/persistant hors politique, annulation sûre | Refus rôle, interruption export, purge et logs sans données | 2 |

## FEA26 — Dashboard et recette MVP locale

### US26 — Comme owner, je veux un tableau de bord lisible et une démonstration locale reproductible.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T089 — Dashboard/reporting UI | Afficher cartes, tableaux, filtres et définitions accessibles | frontend/reporting | P1 | T086, T088, T032 | Loading/empty/error, monnaie et période visibles, export autorisé | RTL filtres/valeur nulle, clavier, erreur et changement tenant | 5 |
| T090 — Isolation des agrégats | Vérifier API/CSV/UI/cache avec tenants A/B | quality/reporting | P0 | T089, T087, T034 | Aucune somme, ligne ou compte de B visible pour A, même réponse tardive | Tests PostgreSQL/API, CSV, Query cache et Playwright A→B | 5 |
| T091 — Recette MVP locale complète | Rejouer démarrage, migrations et seed puis parcours cœur | quality/infra | P0 | T090, T082, T072, T008 | Compose sur environnement neuf, seed idempotent fictif, trois E2E et Stripe test prouvés | Build neuf, redémarrage persistant, seed répété, suites backend/frontend/E2E | 5 |
