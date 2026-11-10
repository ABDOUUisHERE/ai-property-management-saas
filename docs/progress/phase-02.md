# Suivi P02 — architecture exécutable

Autorisation : « continue » de l'utilisateur après fusion de la PR #10, le 2026-11-10.
La CI de `main` a réussi après cette fusion (`6af120f`).

## Issue proposée et plan du lot

Issue locale **T010–T019 — rendre l'architecture exécutable**. Référence :
[critères P02](../backlog/phase-02.md). Branche : `feat/t010-executable-foundations`.

1. T010–T014 : configuration, cycle de vie FastAPI, transactions SQLAlchemy,
   migrations Alembic, contexte explicite, erreurs expurgées et sondes.
2. T015–T017 : contrats OpenAPI versionnés, shell React accessible et client typé.
3. T019 : outbox PostgreSQL, livraison récupérable et consommation idempotente.
4. T018 : images, Compose, contrôles applicatifs et recette sur PostgreSQL réel.

Chaque incrément est vérifié avant commit. Les fonctionnalités métier et
l'authentification applicative restent en P03 et au-delà. La publication du nouveau
lot et sa fusion seront distinguées de l'implémentation locale.

## Validation locale

| Tâches | Résultat et preuves |
| --- | --- |
| T010 | Factory FastAPI et lifespan, configuration Pydantic validée, moteur partagé et unité de travail par contexte ; startup/shutdown et live sans DB testés |
| T011 | Alembic sur PostgreSQL réel : upgrade vide, réexécution, downgrade/upgrade dans une base jetable ; rôle runtime sans CREATE/superuser/BYPASSRLS |
| T012 | Contexte explicite et horloge injectable ; commit volontaire, rollback par défaut et fermeture systématique ; réutilisation du pool sans tenant résiduel |
| T013 | Erreurs `application/problem+json`, request ID validé et logs JSON avec champs autorisés ; exceptions, query strings et secrets de fixtures non réfléchis |
| T014 | Live indépendant, ready vérifiant le schéma et la DB, délais SQL/connexion/pool bornés ; métriques de réponses et latence ; timeout SQL réel testé |
| T015 | Snapshot OpenAPI validé, schémas monnaie/pagination/dates/erreurs et tests de frontières ; différence de contrat bloquante jusqu'à revue/régénération |
| T016 | React/TS strict, Router, Query et dialogue Radix ; shell responsive sans données métier, focus/clavier testés et captures inspectées |
| T017 | Types générés, validation des réponses, expiration et annulation testées ; contexte capturé par appel, clés par organisation, purge du cache et mutations sans retry automatique |
| T018 | Images construites et démarrage Compose vérifié ; contrôles locaux verts ; workflow Actions validé avec actionlint 1.7.12, mais exécution distante P02 encore en attente de publication |
| T019 | Mutation/outbox dans la même transaction ; dispatcher limité au routage, worker sous contexte/RLS ; rollback, crash de publication/effet, doublon et consommation concurrente testés ; perte réelle Redis récupérée avec worker réel |

Résultats : **16 tests d'outillage, 15 tests backend, 9 tests frontend, 3 tests
navigateur réussis**. Ruff lint/format, mypy strict, TypeScript, ESLint, Prettier et
build Vite réussis. L'audit npm ne signale aucune vulnérabilité au moment du
contrôle. Les captures [desktop](../screenshots/p02-desktop.png) et
[mobile](../screenshots/p02-mobile.png) ont été inspectées ; axe ne rapporte pas
de violation sur les écrans d'accueil, guide et dialogue testés. Cela ne certifie
pas tous les futurs parcours WCAG.

Le smoke applicatif a vérifié UI, routage même origine, OpenAPI, schéma prêt et
reçu d'un événement par le dispatcher/worker réels. La recette Redis utilise
une base `pms_test_<UUID>` et deux conteneurs sans volume, créés et supprimés
uniquement par le test ; aucune queue ni donnée d'une autre stack n'est effacée.

## Ajustements vérifiés

- Le port 5173 était déjà publié par le portail FinCore existant. L'interface
  utilise **18173** ; seul `APP_SITE_URL` a changé dans le `.env` local, avec
  égalité vérifiée de tous les secrets avant/après. FinCore n'a pas été modifié.
- Les sondes Celery fondées sur l'import complet de l'outil dépassaient leur
  délai à froid. La sonde lit maintenant un heartbeat privé émis par le worker
  connecté ; le smoke vérifie séparément la consommation réelle.
- Docker Desktop peut réattribuer un port hôte éphémère après redémarrage du
  broker de test. La recette relit ce port ; le worker utilise son DNS interne
  stable. Le test de perte réelle Redis réussit après cet ajustement du harness.
- L'audit signalait `minimatch` dans l'outillage. Un override ciblé de la branche
  10 vers **11.0.1** corrige [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) ; lint,
  génération, tests et build ont été vérifiés avec cette combinaison.
- Les contrastes du libellé d'accueil et des numéros du guide ont été corrigés
  après des échecs réels axe, puis les trois tests navigateur ont réussi.

## Commandes et portée de livraison

Depuis la racine : `uv sync --locked`, `uv sync --project backend --locked`,
`uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`,
`uv run python scripts/check_repository.py`, `uv run python scripts/scan_secrets.py`,
`uv run python scripts/application.py test --broker-recovery` et
`uv run python scripts/application.py smoke`. Images construites avec
`docker compose build` ; processus démarrés avec `docker compose up -d --wait`.
Le bootstrap complet `uv run python scripts/dev.py up` puis le smoke P01
`uv run python scripts/dev.py smoke` ont aussi réussi après les ajustements :
dix processus healthy, migration terminée avec code 0, Auth/DB/Redis/S3 vérifiés.

Dans `backend/` : `uv run mypy`. Dans `frontend/` : `npm ci`/installation
verrouillée, `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`,
`npm run build`, `npm run generate:api`, `npm audit --audit-level=moderate`,
`npx playwright install chromium --only-shell`, `npm run test:e2e`.

Activité distante de ce lot : **0 Issue créée, 0 push, 0 PR publiée, 0 fusion**.
La branche locale et la description de PR sont préparées pour revue. La CI
applicative distante reste à exécuter après autorisation de publication ; cette
porte de livraison P02 n'est pas déclarée franchie. P03 attend un nouvel accord.
La façade Auth, les memberships, le RBAC, les tables métier, les paiements et le
seed métier restent hors du lot. Le warning de dépréciation du transport httpx
du TestClient Starlette est non bloquant et reste à migrer vers httpx2.
