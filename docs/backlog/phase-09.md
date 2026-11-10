# E09 — Livraison et préparation exploitation

Phase de chaque tâche : **P09**. Version : **MVP**. Gate : P08 vérifiée et accord. AWS (T099–T101) reste optionnel ; sans accès/budget, statut « différé », jamais « testé ».

## FEA27 — Durcissement et sécurité

### US27 — Comme entreprise, je veux réduire les surfaces d'attaque avant toute démonstration publique.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T092 — Revue des frontières exposées | Vérifier auth, CSRF, CORS, proxy, débit, uploads et RBAC de toutes routes | security | P0 | T091 | Matrice endpoints/permissions exhaustive, failles critiques corrigées | Requêtes adverses, brute force bornée, headers proxy et A/B | 5 |
| T093 — Expurgation et secrets | Contrôler logs/traces, configuration, rotation et accès opérateur | security/observability | P0 | T092, T013 | Aucun secret/PII de fixture dans artefacts, secrets révocables et droits minimaux | Scan source/images/logs, rotation sur staging/local, erreur fournisseur | 3 |
| T094 — Dépendances et images | Ajouter scans adaptés, versions verrouillées et traitement findings | ci/security | P0 | T093, T018 | Risques critiques traités ou exception explicite, builds reproductibles | Scan dépendances/images, image non-root et vérification lockfiles | 3 |

## FEA28 — Observabilité et continuité

### US28 — Comme exploitant, je veux détecter une panne et restaurer les données avec une preuve.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T095 — Métriques et alertes utiles | Instrumenter API/DB/worker/outbox/rapprochement et suivi d'erreurs | observability | P1 | T091, T014 | Alertes seuils approuvés, dashboards sans PII et corrélation jobs | Panne DB/Redis/email, outbox bloquée et paiement en anomalie | 5 |
| T096 — Sauvegarde et restauration | Documenter et exécuter restauration métier/objets avec cohérence Auth | infra/runbooks | P0 | T091, T093 | Sauvegarde protégée, restauration isolée prouvée, RPO/RTO mesurés | Restore réelle, FK/contraintes/RLS après restore, liens sujet/profil et photos | 5 |
| T097 — Charge et concurrence de recette | Mesurer objectifs D11 et plans SQL sur dataset approuvé | quality/performance | P1 | T095, T059, T090 | Dataset/machine/scénario documentés, p95 et contention mesurés, régressions corrigées | Lectures mixtes, 20 writers unité, backlog worker, profiling SQL | 5 |

## FEA29 — Pipeline complet et AWS optionnel

### US29 — Comme mainteneur, je veux livrer un artefact validé et un déploiement récupérable si autorisé.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T098 — CI de release complète | Consolider qualité, migrations, PostgreSQL, builds et trois E2E | ci | P0 | T094, T097, T082, T090 | Tous jobs obligatoires bloquants, artefacts expurgés, permissions minimales | PR avec échec volontaire contrôlé, E2E auth/réservation/opérations et build propre | 5 |
| T099 — IaC AWS optionnelle | Préparer réseau, ECS, RDS, Redis, S3 et responsabilités Auth | infra/aws | P1 | T098, T096 | D09/budget validés avant provisioning ; plan revu, ressources privées et tags coût | Validation/plan IaC ; intégration extension DB et connectivité si autorisé | 8 |
| T100 — Déploiement staging autorisé | Installer CD OIDC, image par digest, migration unique et smoke tests | infra/aws | P1 | T099 | Aucun secret longue durée, même origine/cookies sûrs, aucune donnée réelle | Déploiement réel autorisé, TLS, readiness, session, Stripe test et worker | 8 |
| T101 — Rollback et incident AWS | Éprouver retour compatible et restauration sur cible autorisée | infra/aws | P1 | T100, T096 | Procédure testée, compatibilité schéma/image et limites de rollback connues | Déploiement échoué, rollback app, restore isolée et alerte | 5 |

## FEA30 — Recette, documentation et clôture

### US30 — Comme évaluateur, je veux reproduire la démonstration et connaître ses limites réelles.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T102 — Conservation et accessibilité finales | Vérifier politique données et parcours clavier/lecteur d'écran critiques | security/ux | P0 | T098, T044 | D07 concrétisée avant données réelles, purge éprouvée, blocages accessibilité corrigés | Anonymisation/purge/backup policy, audit a11y automatique et manuel | 5 |
| T103 — Documentation et démonstration | Compléter README, OpenAPI, runbooks, captures et limites | docs | P1 | T102, T096, T098 | Commandes rejouées, seed fictif, démo sans intégration revendiquée à tort ; AWS indiqué déployé/différé | Relecture sur environnement neuf, liens, exemples API et captures cohérentes | 3 |
| T104 — Recette et version MVP | Vérifier A01–A09, risques ouverts et préparer release si autorisée | release | P0 | T103, T091, T098 ; T101 si AWS choisi | Preuves complètes, bilan réel, décision explicite AWS livré/différé ; tag/release seulement autorisés | Matrice de recette signée, revue preuves et liens GitHub réels | 3 |
