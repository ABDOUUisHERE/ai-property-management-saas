# Qualité, exploitation et livraison proposées

## Définition de terminé

Chaque tâche doit satisfaire ses critères, sa migration si nécessaire, ses preuves de tests, le contrôle des accès, la documentation affectée et les contrôles CI disponibles. Une fonctionnalité n'est pas terminée parce que son écran existe. Chaque phase possède une condition de sortie dans la [roadmap](../roadmap.md) ; en cas d'échec, corriger avant de passer à la suivante et obtenir l'accord de l'utilisateur pour la phase suivante.

## Stratégie de tests

| Niveau | Outils prévus | Preuves importantes |
| --- | --- | --- |
| Domaine backend | pytest, horloge et identifiants injectables | États, arrondis, prix, rôles, génération ménage, frontières |
| API et contrats | httpx + pytest | Codes, schémas, pagination, erreurs, idempotence, CSRF, refus d'accès |
| Intégration DB | PostgreSQL dédié ou Testcontainers, vrai rôle runtime | Migrations, RLS, FK composites, exclusions, verrous, transactions et pool |
| Asynchrone | PostgreSQL + Redis + worker réel en intégration | Arrêt avant/après commit, republication, déduplication, retries, file d'échecs |
| Paiements | Fixtures signées + Stripe test via CLI/compte dédié | Corps brut, signature invalide, répétition, ordre inversé, montant/devise, reprise après timeout |
| Composants UI | Vitest + React Testing Library | Interactions, erreurs, loading/empty, champs et navigation clavier |
| Parcours E2E | Playwright | Auth/tenant, réservation avec conflit, opérations après départ ; paiements si accès disponibles |
| Exploitation | Scripts documentés, environnement isolé | Démarrage neuf, migration existante, restauration, rollback, déploiement optionnel |

SQLite ne remplace pas PostgreSQL pour les preuves d'isolation/concurrence. Tests concurrents avec connexions/transactions distinctes et barrières explicites ; pas de simple boucle séquentielle ni de sleep comme seul mécanisme de synchronisation. Vérifier la base après commit des transactions concurrentes. Tests : confirmation/confirmation, création/création, changement de dates, réservation/maintenance, expiration/webhook, déplacement d'unité et réessais simultanés.

Une fixture multi-tenant possède A et B, un utilisateur A seul, un B seul, un multi-tenant et les trois rôles. Tester listes/détails/mutations, associations vers IDs étrangers, calendars, photos/URL signées, caches, workers, exports, reporting et erreurs ; requête sans contexte et réutilisation A puis B d'une connexion du pool. Interdire aussi le changement de `organization_id` d'une ligne existante.

Pour le ménage, tester la répétition et la concurrence de confirmation/départ, l'annulation d'une tâche planifiée, la panne avant accusé de consommation et la reprise. Pour les paiements, ajouter expiration avant preuve de paiement, annulation pendant Checkout, réponse fournisseur perdue et remboursement répété. Garder la différence entre tests simulés et intégration Stripe réelle dans chaque rapport.

## Configuration et qualité statique

Propositions : Python 3.12+ et `uv`, Ruff lint/format, mypy avec exigences renforcées sur le domaine ; TypeScript strict, ESLint/Prettier, `tsc`, Vitest, build Vite. Choisir une version Python/Node/PostgreSQL supportée et compatible avec images, SDK et AWS au moment du squelette ; épingler dépendances et lockfiles. Ne pas annoncer ici une version « latest » non testée.

Paramètres validés au démarrage par environnement (local/test/staging/production). `.env.example` contient uniquement des noms et exemples non secrets ; `.env` ignoré. Échec rapide si secret absent hors mode explicitement simulé. Stripe live interdit dans la configuration MVP. Timeouts réseau/SQL, pools et limites de payload explicites. Les en-têtes proxy ne sont fiables que depuis le proxy approuvé.

## CI/CD à construire progressivement

Phase 1 : pipeline minimal de contrôle documentaire/configuration et détection de secrets. Phase 2 : installer depuis lockfiles, lint/format/type checking, tests backend/frontend et builds, vérifier les migrations sur PostgreSQL. Phase 3 : isolation réelle obligatoire. Phases métier : ajouter les suites à chaque livraison ; ne pas repousser la qualité à la phase 9.

Avant le jalon MVP, toute PR exécute les jobs backend, frontend, PostgreSQL et les trois E2E critiques auth/réservation/opérations. Artefacts expurgés en cas d'échec ; aucune trace contenant tokens ou payload voyageur. Les changements purement documentaires peuvent utiliser des contrôles adaptés avant que le pipeline applicatif existe, sans prétendre valider l'application.

GitHub Actions : permissions minimales, actions épinglées de façon révisable, dépendances verrouillées, jobs avec délais, annulation des exécutions obsolètes ; aucun secret sur code de fork non approuvé. Audits de dépendances adaptés, scan de secrets et images. Versionner l'OpenAPI et vérifier les changements incompatibles avant fusion. Un scan silencieux n'est pas une preuve de sécurité exhaustive.

CD AWS optionnelle : construire une fois une image identifiée par digest, analyser, déployer staging avec OIDC sans clé AWS longue durée, exécuter migration via job unique avec verrou, smoke tests puis déploiement validé. Préférer migrations expand/contract compatibles avec l'ancienne et la nouvelle version. Rollback applicatif seulement si le schéma reste compatible ; sinon restauration/roll-forward documenté. Ni déploiement ni dépense AWS dans cette session.

## Exploitation et objectifs à approuver

Hypothèses de test, à confirmer en D11 : 50 organisations, 500 unités au total, 100 000 réservations historiques, 20 mutations concurrentes sur une unité pour la recette de conflit et 50 requêtes/s mixtes en charge. Ce sont des dimensions de test proposées, pas des limites d'abonnement.

Objectifs provisoires : p95 de lecture métier ≤ 500 ms et écriture locale ≤ 1 s hors fournisseur externe, mesurés sur environnement et dataset documentés ; disponibilité cible 99,5 % mensuelle si exploitation financée ; RPO ≤ 24 h, RTO ≤ 4 h à démontrer par restauration. Aucun SLA n'est promis avant mesures/budget. Les seuils worker (âge d'outbox, retries, options bloquées) sont à définir selon le temps d'expiration retenu.

Sondes : live = processus vivant ; ready = dépendances strictement requises accessibles et schéma compatible, avec timeout court ; panne email/Stripe signale dégradation sans nécessairement faire redémarrer l'API. Le worker a un heartbeat distinct. Surveiller latences, codes d'erreur, pool DB, conflits 409, retard outbox, échecs définitifs, paiements non rapprochés et stockage.

Logs structurés : instant UTC, niveau, service, environnement, request/job ID, action, résultat ; identifiant d'organisation seulement si nécessaire au diagnostic et accès contrôlé. Interdits dans logs/traces : mots de passe, tokens, corps Auth, cartes, emails et préférences voyageurs. Le suivi d'erreurs est expurgé avant émission. Audit sensible : acteur, action, ressource, instant et changement minimal ; accès limité et conservation D07.

Runbooks à produire et éprouver : démarrage/migrations/seed, sauvegarde/restauration DB et objets, reprise outbox, rapprochement Stripe et remboursement, rotation de secrets/signing keys, retrait utilisateur, fuite tenant, panne Redis/email, déploiement et rollback. Les sauvegardes Auth et métier ont des responsabilités distinctes ; documenter leur cohérence et le lien sujet Auth ↔ profil après restauration.
