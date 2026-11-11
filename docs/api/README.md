# Contrats API P02

Le [snapshot OpenAPI](openapi.json) décrit uniquement les routes livrées :
`GET /health/live` et `GET /health/ready`. Le contrat est disponible aussi sur
`/api/v1/openapi.json` et sa documentation sur `/api/v1/docs`. Les routes métier
seront ajoutées avec leurs tâches ; aucun endpoint métier factice n'est exposé.

Les schémas transversaux versionnés fixent : erreurs Problem Details, pagination
`page >= 1`, `1 <= limit <= 100`, monnaie entière en unités mineures avec code
devise sur trois lettres, dates de séjour `[check_in, check_out)` et instants avec
fuseau obligatoire. Le code devise devra aussi être validé selon les devises
supportées au moment du module métier ; trois lettres seules ne prouvent pas sa
présence dans ISO 4217.

Les erreurs contiennent un code stable et un `request_id`, sans valeurs de champs,
payload fournisseur ni exception brute. Le navigateur affiche un message local
adapté ; le détail arbitraire d'un fournisseur ne devient pas du HTML affiché.

Si une erreur survient après l'envoi des en-têtes, le serveur interrompt le flux
avec une exception expurgée ; il ne peut plus remplacer le statut HTTP. Aucun
second bloc d'en-têtes n'est envoyé. Le compteur `pms_http_stream_failures_total`
et le champ de log `outcome=interrupted` permettent de détecter ce cas même si
le statut initial était 200.

## Modifier un contrat

1. Modifier les schémas Pydantic et leurs exemples/tests dans `backend/`.
2. Exécuter `uv run python scripts/application.py export` depuis la racine.
3. Dans `frontend/`, exécuter `npm run generate:api`.
4. Revoir les différences du snapshot et des types générés. Un changement de
   contrat incompatible exige une migration/version explicite avant fusion.
5. Exécuter les tests de contrat, le typage et `npm run check:api`.

La CI compare le snapshot au schéma généré et les types au snapshot : toute
modification, compatible ou incompatible, rend visible la différence à revoir.
Ce contrôle strict ne prétend pas décider automatiquement de la compatibilité
sémantique métier.

## Sources techniques

- [Cycle de vie FastAPI](https://fastapi.tiangolo.com/advanced/events/).
- [Transactions SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).
- [Livraison et acquittement Celery](https://docs.celeryq.dev/en/stable/userguide/tasks.html).
