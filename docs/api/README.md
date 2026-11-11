# Contrats API P02/P03

Le [snapshot OpenAPI](openapi.json) décrit les sondes et la façade Auth :
GET `/api/v1/auth/csrf`, POST `/api/v1/auth/register`, `/login`, `/logout`,
`/refresh`, `/recovery/request`, `/recovery/confirm`, GET `/api/v1/me`,
GET `/health/live` et `/health/ready`.
Les chemins abrégés partagent `/api/v1/auth`. Le contrat est disponible sur
`/api/v1/openapi.json` et sa documentation sur `/api/v1/docs`.

## Authentification par cookie

1. Appeler GET `/api/v1/auth/csrf` avec les cookies même origine. Conserver son
   `csrf_token` en mémoire ; le contexte anonyme est un cookie HttpOnly.
2. Envoyer les mutations avec `Origin` égal à l'origine configurée et l'en-tête
   `X-CSRF-Token`. Login retourne profil et expiration ; le seul identifiant de
   session navigateur est un cookie opaque HttpOnly, SameSite=Lax, Secure en HTTPS.
3. Après login, obtenir un nouveau jeton CSRF, lié à la session, avant refresh ou
   logout. GET `/me` ne nécessite pas de CSRF et relit la session persistée.
4. Logout révoque localement avant l'appel fournisseur et expire les cookies.
   Une erreur `session_expired` exige un login ; `session_busy` (409) signale un
   refresh concurrent. Les mutations ne sont pas réessayées automatiquement.

Le nom de cookie est `pms_session` en HTTP local explicite, `__Host-pms_session`
en HTTPS. Aucun access/refresh token Supabase n'est retourné dans le JSON ou
stocké dans localStorage. Toutes les réponses Auth et `/me` sont `no-store`.
Les corps Auth sont bornés à 8 Kio, les champs sensibles supplémentaires refusés.
Les adresses fictives réservées `.test` sont acceptées pour Mailpit, sans requête
DNS de validation ; l'autorité Auth vérifie toujours l'identité et l'email.

L'inscription renvoie 202 générique pour succès, refus ou throttling fournisseur ;
la limite locale renvoie 429 et la panne fournisseur 503 sans détail d'existence.
Redis applique atomiquement les fenêtres : 30 mutations Auth/minute/source,
60 CSRF/minute/source, 10 login/minute/email et 5 inscriptions/heure/email.
Les clés Redis sont des HMAC, sans IP/email en clair. Un Redis indisponible bloque
ces opérations par 503. Les en-têtes forwarded ne font pas autorité : derrière
le proxy Compose, la limite source est partagée par ses utilisateurs. Une future
configuration de proxies de confiance devra être explicite avant exploitation.

## Récupération de compte

POST `/api/v1/auth/recovery/request` accepte seulement `email` et renvoie 202
`{"status":"accepted"}` pour compte connu/inconnu et refus/throttling fournisseur.
La limite locale est de cinq demandes par heure et email haché ; les protections
Origin/CSRF et la limite par source restent obligatoires. L'URL de retour est
fixée côté serveur à l'origine configurée + `/auth/reset` ; tout champ client
`redirect_to` est refusé. Les pannes fournisseur renvoient 503 générique.

Le template Supabase utilise un lien `/auth/reset#token_hash=…` : le fragment
n'est pas envoyé aux serveurs HTTP. L'interface T031 devra le retirer de l'URL
immédiatement et conserver le jeton uniquement en mémoire. Aucun GET ne consomme
le jeton. POST `/api/v1/auth/recovery/confirm` reçoit `token_hash` (56 caractères
hexadécimaux) et `password` (12–128 caractères) ; Supabase vérifie exclusivement
le type `recovery`, l'expiration d'une heure et l'usage unique.

Avant le changement distant, une transaction pose une barrière par sujet :
sessions antérieures invalidées et login bloqué. Les logins commencés avant la
barrière sont également refusés, même si leur réponse fournisseur arrive après.
Un lease de 30 secondes possède un propriétaire unique, sans transaction SQL
pendant le réseau. Timeout, refus de mot de passe ou réponse tardive laisse la
barrière fermée : demander un nouvel email et reprendre après le lease. Cette
option privilégie la révocation à la continuité de connexion après échec.

Le succès renvoie 204, expire les cookies locaux et exige un nouveau login ;
il ne connecte jamais automatiquement le navigateur. Jeton invalide/expiré/
réutilisé : 401 ; récupération déjà en cours ou réponse tardive : 409.
La révocation des anciennes sessions est logique et immédiate à la résolution ;
leurs ciphertexts restent soumis à la durée et à la future purge des sessions.
## Organisations

Ces routes exigent une session opaque résolue ; le sujet et l'acteur ne peuvent
pas être fournis dans le JSON. POST `/api/v1/organizations` accepte `name`
(1–120 caractères, sans contrôles) et `request_id` (UUID d'idempotence).
La transaction crée l'organisation et son premier owner : 201 initialement,
200 pour la répétition du même nom et de la même clé par le même acteur ;
409 si cette clé est réutilisée avec un autre nom. Les champs `role`, `created_by`
ou `organization_id` sont refusés. Origin/CSRF restent obligatoires.

GET `/api/v1/organizations` liste uniquement les appartenances actives de
l'utilisateur. GET `/api/v1/organizations/current` utilise `X-Organization-ID`
comme sélecteur et relit sa membership active avant de construire le contexte
serveur. Sélecteur absent/invalide : 422 ; organisation étrangère, inexistante
ou appartenance retirée : 404. Session invalide : 401. Deux onglets peuvent
envoyer des sélecteurs différents ; aucun tenant actif global n'est stocké.
Les réponses sont `no-store`, les corps JSON limités à 8 Kio.

La voie SQL de bootstrap autorise seulement le créateur, comme owner actif,
sur une organisation créée dans la transaction courante. Une FK différée
interdit le commit sans son premier membre ; la clé composite de membership
interdit les doublons. Le runtime ne possède pas encore UPDATE/DELETE sur ces
tables. Les changements de membres, l'audit sensible et les permissions de
ressources restent à livrer par T025–T030. Les écrans Auth restent à livrer.

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
