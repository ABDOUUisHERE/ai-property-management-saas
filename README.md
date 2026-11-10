# AI-Powered Property Management SaaS

Plateforme de gestion de locations de courte durée pour plusieurs entreprises indépendantes : biens et unités, voyageurs, réservations, paiements de test, ménage, maintenance et reporting. L'assistant IA est une extension V3, sans dépendance du MVP.

**État au 10 novembre 2026 : cadrage validé, fondations P01 publiées et en revue.** Le dépôt possède les documents de conception, un environnement Docker de six services, des outils de bootstrap, leurs tests et une CI GitHub Actions exécutée avec succès. FastAPI, React et les fonctionnalités métier commencent en P02 et ne sont pas encore implémentés. Aucun déploiement AWS n'est réalisé. Les preuves réelles sont consignées dans [le suivi P01](docs/progress/phase-01.md).

[Dépôt privé](https://github.com/ABDOUUisHERE/ai-property-management-saas) · [PR des fondations](https://github.com/ABDOUUisHERE/ai-property-management-saas/pull/10) · [CI validée sur a4f4f01](https://github.com/ABDOUUisHERE/ai-property-management-saas/actions/runs/42837783466)

## Référence et documents

- [Cahier des charges v1.0](property_management_saas_cahier_des_charges.md) : référence fonctionnelle et technique, conservée sans modification.
- [Analyse et traçabilité](docs/architecture/analysis.md) : périmètre, exigences, critères de recette et correspondance avec le backlog.
- [Architecture](docs/architecture/README.md) : système, modèle métier, API, frontend et qualité.
- [Décisions validées, paramètres ouverts et risques](docs/architecture/risks-decisions.md).
- [Six ADRs acceptés](docs/adr/README.md) : l'acceptation du choix AWS ne vaut pas autorisation de déployer.
- [Backlog](docs/backlog/README.md) : Epic → Feature → User Story → Technical Task.
- [Roadmap et conditions de sortie](docs/roadmap.md).
- [Organisation GitHub proposée](docs/github-workflow.md).
- [Publication GitHub et limites de configuration](docs/github-publication-plan.md).
- [Vocabulaire métier](GLOSSARY.md) et [règles Codex](AGENTS.md).

## Architecture proposée

Monolithe modulaire FastAPI, frontend React/TypeScript et API `/api/v1`. PostgreSQL porte les transactions et contraintes d'intégrité. Supabase Auth est proposé comme unique autorité d'authentification ; les organisations et permissions restent sous contrôle du backend. Redis sert aux tâches asynchrones et au cache, sans décider de l'attribution d'une unité. Stockage objet privé S3-compatible. Stripe Checkout fonctionne exclusivement en mode test dans le MVP.

Le déploiement AWS est optionnel et conditionné à la disponibilité des accès, du budget et à une validation explicite. Les intégrations de canaux V2 utilisent d'abord un simulateur ; aucune intégration officielle Airbnb/Booking.com n'est revendiquée.

## Démarrer les dépendances locales

Prérequis : Git, uv et Docker Desktop/Engine avec Compose et moteur Linux actif. Depuis la racine :

```powershell
uv sync --locked
uv run python scripts/dev.py init
uv run python scripts/dev.py up
uv run python scripts/dev.py smoke
```

`init` génère les credentials locaux dans `.env`, ignoré par Git, et préserve les valeurs existantes. `up` lance Compose et attend les sondes. Après l'initialisation, `docker compose up --build` est également utilisable. Le [runbook](docs/runbooks/local-development.md) décrit les ports, l'arrêt, la reprise, les contrôles et les limites.

Services : PostgreSQL métier, PostgreSQL Auth isolé, Supabase Auth, Redis, Mailpit et stockage S3-compatible RustFS. Mailpit : `http://127.0.0.1:18025`. Auth : `http://127.0.0.1:19999/health`. Aucun compte cloud requis ; tous les ports publiés sont liés à la boucle locale.

## Validation et limites actuelles

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_repository.py
uv run pytest
uv run python scripts/scan_secrets.py
```

Les 15 tests actuels concernent l'outillage et la validation de configuration/JWT. La recette réelle couvre Auth/email/JWKS/session, rôles PostgreSQL, Redis et objets privés S3. Les jobs GitHub Actions `quality` et `infrastructure` ont réussi sur `a4f4f01`, avec 15 tests et le smoke réel des six services. Les checks du dernier HEAD sont consultables dans la PR.

Les migrations Alembic métier, seed métier, OpenAPI, tests backend/frontend et E2E applicatifs restent planifiés. Aucun résultat applicatif, intégration Stripe ou déploiement AWS n'est revendiqué. Captures, démo et badges seront ajoutés lorsqu'ils existent.

## Prochaine étape

Revoir la PR P01, obtenir l'accord de fusion, puis l'accord avant P02. Les neuf Issues P01 et les neuf jalons sont publiés ; les Issues restent ouvertes pour la revue. La licence reste à choisir. La protection obligatoire de `main` a été refusée par l'offre GitHub actuelle pour ce dépôt privé ; la revue et la CI restent appliquées par convention.
