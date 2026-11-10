# Suivi P01 — fondations locales

Date : 2026-11-10. Autorisations : cadrage/backlog (« je valide »), reprise de Docker, publication GitHub (« oui »), puis fusion de la PR #10 (« continue fusionne »). La fusion est réalisée sur `6af120f` et sa [CI après fusion a réussi](https://github.com/ABDOUUisHERE/ai-property-management-saas/actions/runs/42842746766). P02 a ensuite été autorisée (« continue ») ; voir [son suivi](phase-02.md). Aucune dépense AWS n'est autorisée.

## Lot et plan

Références : **T001/T002, puis T005–T009**, et publication T003/T004 après autorisation. Conventions/décisions → Git → Auth/Docker → outils/configuration → contrôles/CI → dépôt, jalons, Issues et PR. Les ressources publiées sont listées ci-dessous.

## État des tâches

| Tâche | État actuel | Preuve / reste à vérifier |
| --- | --- | --- |
| T001 | Réalisée localement | CONTRIBUTING, règles actualisées et six ADRs acceptés ; liens contrôlés |
| T002 | Réalisée localement | Git autonome, main et branche `feat/t001-local-foundations` ; identité associée au compte ; secrets exclus ; commits vérifiés après contrôles |
| T003 | Publiée, options documentées | [Dépôt GitHub](https://github.com/ABDOUUisHERE/ai-property-management-saas), `origin`, main et branche de travail, neuf jalons ; licence ouverte et Project non configuré |
| T004 | PR fusionnée | Neuf Issues P01 avec dépendances, labels et milestone ; [PR #10](https://github.com/ABDOUUisHERE/ai-property-management-saas/pull/10) fusionnée ; Issues encore ouvertes pour le suivi formel |
| T005 | Vérifiée localement | Signup, Mailpit, confirmation, login, ES256/JWKS, refresh/logout réussis sur environnements principal et neuf |
| T006 | Vérifiée localement | Six services healthy, réseaux/volumes séparés, ports loopback, images par digest, rôles DB restreints |
| T007 | Réalisée localement | Python 3.12.12 via uv, lockfile, secrets locaux générés/ignorés ; frontend reporté à P02 |
| T008 | Vérifiée localement | Six services démarrés sur volumes entièrement neufs ; smoke complet ; persistance PostgreSQL/Redis/S3 après redémarrage prouvée |
| T009 | Vérifiée localement et sur Actions | Jobs [quality et infrastructure réussis](https://github.com/ABDOUUisHERE/ai-property-management-saas/actions/runs/42837783466) sur `a4f4f01` : 15 tests et smoke des six services |

## Vérifications et observations

- GitHub CLI authentifié au compte `ABDOUUisHERE`. L'API `/user/emails` n'est pas accessible avec les scopes présents ; aucun élargissement d'accès n'a été demandé. L'email Git local correspond néanmoins à un commit publiquement attribué au même compte par l'API GitHub. Cette preuve d'association ne nécessite pas d'imprimer l'email ni de modifier la configuration globale.
- Docker Desktop était en pause ; l'utilisateur l'a repris. Les autres stacks Docker existantes ne sont pas modifiées.
- Le premier port PostgreSQL envisagé (`55432`) appartient à une plage d'exclusion Windows. Les ports par défaut ont été déplacés sous 30000, sans changer les secrets déjà générés.
- Les migrations GoTrue exigent un rôle `postgres`. La base Auth isolée lui fournit un rôle de compatibilité **NOLOGIN**, sans privilège superuser. Le rôle GoTrue reste propriétaire de son schéma, sans accès à la base métier. La correction a été éprouvée sur des volumes entièrement neufs.
- Une sonde Unix PostgreSQL signalait la base prête pendant le serveur temporaire d'initialisation ; GoTrue échouait alors transitoirement sur sa connexion TCP. La sonde attend maintenant TCP sur `127.0.0.1`. Après suppression des seuls volumes de validation créés pour la recette, un démarrage neuf et le parcours complet ont réussi.
- Un faible décalage d'horloge entre Windows et Docker a fait rejeter un `iat` récent lors d'un essai. La vérification de recette utilise une tolérance explicite de 5 secondes ; les tests conservent les refus d'issuer/audience incorrects et de token daté d'une minute dans le futur.
- Les tests d'outillage couvrent non-écrasement des clés, refus de cible distante, configuration invalide et signature ES256 ; ils ne sont pas des tests métier.
- Gitleaks 8.30.1 est téléchargé depuis la release officielle et vérifié par SHA-256 épinglé. Le test du détecteur utilise un token synthétique ; les secrets générés dans `.env` ne sont jamais affichés.

## Commandes et preuves

Commandes exécutées : `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`, `uv run python scripts/check_repository.py`, `uv run python scripts/scan_secrets.py`, `docker compose config --quiet`, `uv run python scripts/dev.py up`, `uv run python scripts/dev.py smoke`.

La recette a été répétée avec `--env-file .local/fresh-validation.env`, projet isolé `pms_p01_validation`, cinq volumes neufs et ports distincts. Un probe fictif PostgreSQL, une clé Redis et un objet S3 ont conservé leur valeur après `restart` ; les trois probes ont été nettoyés. Aucun volume de l'environnement principal ni des autres projets n'a été effacé.

Résultats : **15 tests d'outillage réussis** ; Ruff lint/format réussis ; liens locaux, 120 tâches et dépendances valides ; Gitleaks avec test du détecteur réussi ; six services healthy et parcours Auth/S3/DB/Redis réussi. Au repos lors d'une mesure ponctuelle, les six conteneurs principaux utilisaient environ 277 MiB au total ; ce n'est pas une garantie de capacité en charge.

La syntaxe du workflow Actions a été vérifiée avec actionlint **1.7.12**, sans erreur. La CI distante a ensuite réussi sur `a4f4f01`, avec preuves des 15 tests, du scanner et du parcours Auth/S3/DB/Redis dans ses logs. Les checks du dernier HEAD sont consultables dans la PR. La façade de session, RLS métier, OpenAPI, Alembic, seed et tests métier restent à implémenter à partir de P02/P03.

## Portée restante

Le volet technique P01 est vérifié, publié et fusionné. Les neuf Issues restent ouvertes pour le suivi formel des critères. La protection de `main` avait été refusée avec HTTP 403 lorsque le dépôt était privé ; sa visibilité a depuis été observée publique, sans modification par l'agent. Le Project optionnel exige un scope d'écriture absent. La licence reste à choisir. Les détails techniques ci-dessus constituent les preuves historiques P01 ; le schéma et Compose évoluent dans P02.

Activité réelle P01 : **1 dépôt créé initialement privé, 9 jalons, 9 Issues, 1 PR publiée puis fusionnée**. Les fondations et le commit de suivi documentaire sont intégrés à `main` par `6af120f`. Les contributions visibles sur le profil GitHub ne sont pas déduites de ces nombres.

## Ressources GitHub vérifiées

| Tâche | Issue |
| --- | --- |
| T001 | [#1](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/1) |
| T002 | [#2](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/2) |
| T003 | [#3](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/3) |
| T004 | [#4](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/4) |
| T005 | [#5](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/5) |
| T006 | [#6](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/6) |
| T007 | [#7](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/7) |
| T008 | [#8](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/8) |
| T009 | [#9](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/9) |

[Jalons P01–P09](https://github.com/ABDOUUisHERE/ai-property-management-saas/milestones) ; [PR #10](https://github.com/ABDOUUisHERE/ai-property-management-saas/pull/10).
