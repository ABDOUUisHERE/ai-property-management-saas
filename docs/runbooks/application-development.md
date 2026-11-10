# Développement applicatif P02

Pré requis : ceux du [démarrage local](local-development.md), plus Node 24 et
npm 11 pour travailler sur le frontend hors Docker. Les dépendances Python de
la racine concernent l'outillage ; celles du backend sont verrouillées dans
`backend/uv.lock`. Le frontend utilise npm et `frontend/package-lock.json`.
TypeScript 5.9 est choisi pour respecter les peer dependencies du générateur
OpenAPI ; ne pas utiliser `--force` pour ignorer une incompatibilité.

## Démarrage

Depuis la racine :

```powershell
uv sync --locked
uv run python scripts/dev.py init
uv run python scripts/dev.py up
uv sync --project backend --locked
uv run python scripts/application.py smoke
```

`init` conserve les secrets existants. Sur un `.env` P01, il ajoute seulement le
nouveau secret du dispatcher. `up` prépare le rôle dédié sur les volumes existants,
construit les images et exécute le job Alembic avant API/worker/dispatcher. Il
attend les sondes des processus persistants. L'interface est sur
`http://127.0.0.1:18173`, l'API directe sur `http://127.0.0.1:18000`.

L'interface proxifie `/health` et `/api` vers l'API sur la même origine. Les logs
d'accès Nginx/Uvicorn sont désactivés ; les logs HTTP applicatifs utilisent une
liste de champs autorisés, sans query string, corps ou en-têtes.

## Sans reconstruire les images

```powershell
uv run python scripts/application.py prepare
uv run python scripts/application.py migrate
uv run python scripts/application.py api
```

Dans un second terminal, depuis `frontend/`, `npm ci` puis `npm run dev`.
Arrêter d'abord les seuls conteneurs `api`/`ui` si leurs ports sont déjà occupés.
Le démarrage des seules dépendances reste possible avec les noms de services
explicites : `docker compose up -d postgres auth-db auth redis mailpit storage`.

## Tests et migrations

```powershell
uv run python scripts/application.py test --broker-recovery
```

Cette commande active explicitement les tests PostgreSQL et fournit le secret
administrateur au seul processus de test. Avec `--broker-recovery`, les images
Compose doivent être déjà construites ; deux conteneurs jetables prouvent la
récupération après perte d'un message Redis. Sans cette option, seul ce test
est explicitement ignoré. La fixture crée sa propre base
`pms_test_<UUID>`, vérifie upgrade/réexécution/downgrade/upgrade, puis supprime
uniquement cette base. Aucun rollback de migration n'est lancé sur la base de
développement. Les sorties pytest masquent les secrets connus de l'environnement.

Dans `backend/` : `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy`. `uv run pytest -m 'not integration'` fonctionne sans services.
Dans `frontend/` : `npm run lint`, `npm run format:check`, `npm run typecheck`,
`npm test`, `npm run build` et `npm run check:api`.

Pour les tests navigateur : `npx playwright install chromium --only-shell`, puis
`npm run test:e2e` avec Compose lancé. Les captures locales sont produites dans
`.local/` ; celles revues pour la livraison sont dans `docs/screenshots/`.

Pour restaurer après un changement local de schéma, privilégier une sauvegarde
et une nouvelle base locale. `alembic downgrade base` détruit les événements et
reçus P02 ; son test est réservé à la base jetable. Ce n'est pas une stratégie
de rollback de données de production.

## Outbox

La transaction autorisée insère `outbox_events` et ses `outbox_deliveries`.
Le dispatcher utilise `pms_dispatcher` : lecture/mise à jour des seules métadonnées
de livraison, sans accès au contenu des événements ni aux tables métier.
Il réserve un lot avec `SKIP LOCKED`, commit un délai de reprise de 30 secondes,
puis publie dans Redis hors transaction. Une livraison est répétée jusqu'à son
reçu durable, même si le message précédent a été perdu par Redis.

Le worker reçoit seulement les identifiants. Il relit le contenu sous RLS avec
un contexte système de l'organisation, verrouille la livraison et commit effet,
reçu unique et fin de livraison ensemble. Le seul consommateur actuel est
`system.probe`, qui vérifie l'infrastructure sans effet métier. Les futurs
consommateurs revalideront les droits selon la nature du travail.

Une erreur du consommateur persiste un code expurgé ; après huit tentatives de
dispatch, elle devient un échec durable consultable en base. Une panne du broker
ne marque jamais à elle seule un effet terminé. La commande `smoke` conserve un
événement de sonde fictif et son reçu, sans donnée personnelle.
