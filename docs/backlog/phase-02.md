# E02 — Architecture exécutable

Phase de chaque tâche : **P02**. Version : **MVP**. Gate : P01 vérifiée et accord de changement de phase.

## FEA04 — Fondations backend et données

### US04 — Comme développeur backend, je veux des frontières stables et un démarrage observable.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T010 — Bootstrap FastAPI | Assembler application, configuration et DI par requête | core | P0 | T008 | `/api/v1`, cycle de vie explicite, configuration validée et aucun état tenant global | Startup/shutdown, config invalide, isolation de sessions | 3 |
| T011 — SQLAlchemy et Alembic | Séparer rôle migration et runtime, installer schéma versionné | database | P0 | T010 | Migration initiale, transactions explicites, conventions FK/index, aucun create_all production | Upgrade base vide, rollback raisonnable, seconde exécution, rôle runtime | 5 |
| T012 — Contexte de requête | Définir acteur/tenant, horloge et unité de travail injectables | core | P0 | T011 | Pas de tenant implicite ; rollback et fermeture systématiques | Transaction échouée, absence contexte, pool réutilisé | 3 |
| T013 — Exceptions et logs | Centraliser erreurs et logs structurés expurgés | core | P0 | T010 | Format HTTP stable, request ID, absence de payload sensible | Mapping erreurs, erreur inattendue, fixtures de secrets expurgés | 3 |
| T014 — Sondes et métriques initiales | Exposer live/ready et instrumentation de base | observability | P1 | T011, T013 | Sondes sans secret, dépendances critiques bornées, métriques latence/erreurs | DB indisponible, timeout, live indépendant | 2 |

## FEA05 — Contrats et socle frontend

### US05 — Comme utilisateur, je veux une interface accessible avec des erreurs cohérentes.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T015 — Contrats OpenAPI | Fixer erreurs, pagination, monnaie, dates et exemples API | api | P1 | T012, T013 | Schémas versionnés, codes documentés, snapshot et génération client possibles | Validation OpenAPI, exemples, détection changement incompatible | 3 |
| T016 — Socle React accessible | Initialiser Vite/TS strict, router, Query et composants accessibles | frontend | P1 | T008 | Shell responsive, navigation clavier et états système | Build, typage, Vitest shell et focus | 3 |
| T017 — Client API typé | Générer types, gérer erreurs et contexte tenant par appel | frontend/api | P0 | T015, T016 | Pas de modèle SQL exposé, query keys tenant, erreurs/réessais contrôlés | Réponse invalide, expiration, annulation requête et mutation sans retry aveugle | 3 |

## FEA06 — Livraison et asynchrone de base

### US06 — Comme mainteneur, je veux détecter les régressions et persister les effets différés.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T018 — CI applicative et images | Ajouter lint/format/types/tests/builds et services API/UI à Compose | ci/infra | P0 | T009, T014, T017 | Images exécutables, checks backend/frontend et PostgreSQL réels sur PR | Build propre, migrations en CI, échec d'un contrôle bloquant | 5 |
| T019 — Outbox et worker minimal | Créer événement durable, dispatcher et reçu consommateur | core/workers | P0 | T011, T012 | Commit atomique métier/outbox, redelivery récupérable, worker contextualisé | Rollback sans événement, crash publication, doublon, perte Redis | 5 |
