# Incrément P03 — Profils et sessions persistantes

T020/#22 et T021/#23, suite autorisée le 2026-11-11 par « continue max de
contributions ». Continuer la branche et la PR #37 ; aucune nouvelle Issue ne
duplique ces tâches. La fusion et P04 ne sont pas autorisées par cette reprise.

## Plan avant implémentation

1. Migration `0002_identity` : `users` avec sujet Auth unique et immuable,
   `auth_sessions` avec hash opaque, jetons chiffrés, durée absolue, version,
   lease de refresh et révocation. RLS forcée, rôle runtime sans bypass ; droits
   de colonnes interdisant le changement de sujet, propriétaire et durée maximale.
2. Repository SQL : transactions avec sujet vérifié pour le bootstrap et capacité
   de session pour la résolution. Aucune organisation fictive ni exemption RLS
   générale. Un profil n'est visible qu'à son sujet ou à sa propre session active.
3. Service de session : login récupérable, résolution, renouvellement coordonné
   et logout. Révoquer avant tout appel de logout fournisseur ; aucune transaction
   ni connexion SQL conservée pendant un appel réseau. Timeout/crash de refresh
   impose une nouvelle connexion, sans réutiliser un refresh token ambigu.
4. Tests PostgreSQL : refus sans contexte/identité étrangère, unicité concurrente,
   pool réutilisé, rollback, durées, rotation de chiffrement, refresh concurrent,
   lease expiré, panne fournisseur et logout pendant un refresh.
5. Étendre la recette Auth/Mailpit réelle au profil et à la session persistés,
   puis exécuter les contrôles locaux et la CI du nouveau HEAD.

## Critères et limites

Le token opaque compte 256 bits aléatoires ; seul SHA-256 est conservé. Les jetons
fournisseur sont chiffrés avec les primitives du premier incrément. Durée absolue
par défaut : 24 h, configurable au plus 7 jours ; elle ne glisse pas au refresh.
Un lease de refresh dure 30 s, au-delà des délais bornés de l'adapter. Un concurrent
reçoit un refus temporaire explicite ; un lease expiré révoque au lieu de relancer
un appel potentiellement déjà réussi. Les effets sont validés par version et
propriétaire du lease pour empêcher une résurrection après logout.

Le service vérifiera les JWT stockés lors de la résolution, puis relira l'état
local avant de rendre le profil. Une panne JWKS sans refresh bloque l'accès mais
ne détruit pas la session. La révocation locale prend effet à la prochaine
résolution ; une commande déjà autorisée peut achever sa transaction.

La restauration privilégie une nouvelle base sauvegardée et une migration avant.
Le downgrade supprime profils et sessions : exclusivement testé sur la base
jetable. La perte du trousseau impose la reconnexion, jamais un stockage clair.
La purge périodique des sessions révoquées/expirées reste à ajouter avant
exploitation avec données réelles ; aucune donnée personnelle réelle n'est utilisée.

La tranche persistante a réussi sur PostgreSQL local (123 tests réussis, test de
perte Redis explicitement exclu). La suite couvre T022/#24 avant d'exposer les
routes : configuration de trousseau séparée, cookies HttpOnly/SameSite avec Secure
obligatoire en HTTPS, jeton CSRF signé lié à la session et vérification stricte
Origin, refus CORS des origines étrangères et limite atomique de débit Redis.
La panne du limiteur doit échouer fermée. Les secrets ne vont qu'au processus API.

Contrats prévus : GET `/api/v1/auth/csrf`, POST register/login/logout/refresh et
GET `/api/v1/me`. L'inscription renvoie toujours un accusé générique pour les
refus du fournisseur ; la panne reste 503. Login ne retourne que profil et durée
de session. Aucun access/refresh token fournisseur ni identifiant opaque dans le
JSON. Cookies, réponses et erreurs Auth portent `Cache-Control: no-store`.
Les tests HTTP couvrent refus avant toute mutation, cookie flags, absence de
tokens dans JSON/OpenAPI, erreurs normalisées, throttling et logout immédiat.
