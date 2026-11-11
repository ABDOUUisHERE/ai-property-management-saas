# P03 — Identité et isolation

## Autorisation et point de départ

Le 2026-11-11, l'utilisateur a répondu « fait le meilleur choix » à la proposition
de fusionner P02 puis démarrer P03. Choix exécuté : [PR #21](https://github.com/ABDOUUisHERE/ai-property-management-saas/pull/21)
fusionnée sur `04726fe`, après les huit checks réussis du HEAD `403fb81`.
Les Issues P02 #11–#20 sont fermées par cette fusion. P03 est autorisée ; P04
attend un nouvel accord.

## État actuel de la livraison

La [PR #37](https://github.com/ABDOUUisHERE/ai-property-management-saas/pull/37)
contient maintenant les profils persistants, les sessions opaques révocables et
la façade HTTP protégée de T020–T022. Ces trois tâches sont implémentées et
vérifiées localement, en attente de la CI du nouveau HEAD et de livraison revue.
La PR n'est pas fusionnée. Le [plan de l'incrément](p03-session-plan.md) et
[les contrats HTTP](../api/README.md) détaillent comportement et limites.
T023–T034 restent à réaliser ; aucune isolation d'organisation n'est encore prouvée.

## Premier incrément publié

Branche `feat/t020-identity-foundations`, depuis `04726fe`.
[PR #37](https://github.com/ABDOUUisHERE/ai-property-management-saas/pull/37),
commits `595f45e` (adapter, vérification, chiffrement) et `cc719a8`
(test avec Auth/Mailpit réels).

- T020 : adapter Supabase pour inscription, login, refresh et logout, sans second
  mot de passe stocké ni jeton envoyé au navigateur.
- T021 : vérification ES256/JWKS avec issuer/audience/claims stricts, rotation
  bornée du cache, chiffrement authentifié lié à une session et à son sujet.
- Tester les refus, les erreurs fournisseur, les rotations et la réception
  réelle de l'email local dans la CI.

Ce premier incrément laissait T020/T021 partielles. L'incrément suivant, décrit
ci-dessous, ajoute le profil SQL, la persistance, la coordination des refresh
et les routes HTTP protégées ; le présent paragraphe conserve l'historique.

Docker Desktop est observé arrêté localement au démarrage de P03. Les tests qui
exigent la pile réelle sont vérifiés sur les runners Linux de GitHub, sans
revendiquer une réussite locale avec Docker arrêté.

## Issues du backlog

Les tâches T020–T034 sont publiées dans le jalon
[P03](https://github.com/ABDOUUisHERE/ai-property-management-saas/milestone/3).
Leurs critères restent ouverts jusqu'à preuve et livraison complète.

| Tâche | Issue | État de cet incrément |
| --- | --- | --- |
| T020 Adapter et profil | [#22](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/22) | Implémentée et testée ; livraison en revue |
| T021 Sessions | [#23](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/23) | Implémentée et testée ; livraison en revue |
| T022 Transport Auth | [#24](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/24) | Implémentée et testée ; livraison en revue |
| T023 Récupération | [#25](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/25) | À faire |
| T024 Organisations | [#26](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/26) | À faire |
| T025 Invitations | [#27](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/27) | À faire |
| T026 Membres | [#28](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/28) | À faire |
| T027 RLS | [#29](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/29) | À faire |
| T028 Contexte tenant | [#30](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/30) | À faire |
| T029 Audit | [#31](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/31) | À faire |
| T030 RBAC | [#32](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/32) | À faire |
| T031 Écrans Auth | [#33](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/33) | À faire |
| T032 Sélection tenant | [#34](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/34) | À faire |
| T033 Gestion équipe UI | [#35](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/35) | À faire |
| T034 Recette | [#36](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/36) | À faire |

## Contrats du premier incrément

`modules/identity/provider.py` possède la traduction HTTP Supabase. Il ne renvoie
pas la réponse d'inscription et exige un email confirmé, un sujet et un ID de
session vérifiés. Le transport interdit les redirections et les proxies hérités,
borne taille et délais, masque les réponses d'erreur et ne réessaie aucune mutation.
Les URLs et l'issuer proviennent de la configuration, jamais du JWT. Le transport
HTTP local vise seulement le loopback ou le service Compose `auth` ; staging et
production exigent HTTPS. Cet adapter cible l'API Auth directe ; son assemblage
au bootstrap et une éventuelle passerelle hébergée restent à configurer.

`verification.py` accepte uniquement ES256/P-256, audience et rôle `authenticated`,
sujet/session UUID non nuls, dates numériques entières et durée de jeton au plus
d'une heure (900 secondes dans la pile locale). Tolérance d'horloge : 5 secondes.
Le cache JWKS expire après 60 secondes ; un `kid` nouveau provoque au plus une
requête supplémentaire par 10 secondes et par instance. Une clé retirée peut
rester acceptée pendant ce TTL ; une panne après expiration échoue sans utiliser
les clés périmées. Aucun rôle d'organisation n'est déduit du JWT.

Un refresh doit conserver sujet et session fournisseur. Timeout, erreur ou réponse
incohérente produit `RefreshUncertain` : le futur service devra révoquer localement
et demander un login. L'adapter seul ne constitue donc pas encore une session
opaque ni une garantie de révocation locale. Logout demande explicitement la
révocation de cette session fournisseur (`scope=local`).

`vault.py` utilise AES-256-GCM avec nonce aléatoire de 96 bits. Les données
authentifiées lient version, ID de clé, hash de session et sujet : copier un
ciphertext vers une autre session est refusé. Le trousseau accepte jusqu'à huit
clés et écrit avec la clé active ; les anciennes restent lisibles jusqu'à
ré-encryption des lignes ou expiration des sessions, puis sont retirées. Aucune
clé réelle n'est créée ni stockée dans le dépôt ou la base par cet incrément.
Le service à venir appliquera l'expiration et la révocation en base.

Références vérifiées : [JWT Supabase](https://supabase.com/docs/guides/auth/jwts),
[rotation des clés](https://supabase.com/docs/guides/auth/signing-keys),
[vérification PyJWT](https://pyjwt.readthedocs.io/en/latest/api.html),
[délais HTTPX](https://www.python-httpx.org/advanced/timeouts/),
[AEAD cryptography](https://cryptography.io/en/latest/hazmat/primitives/aead/).

## Validation locale du 2026-11-11

- Dans `backend/`, `uv run pytest -m 'not integration'` : **85 réussis**, sept
  tests d'intégration exclus. `uv run mypy` : 23 fichiers sans erreur.
- À la racine, `uv run pytest` : **17 réussis**. `uv run ruff check .` et
  `uv run ruff format --check .` réussissent.
- `uv run python scripts/check_repository.py` : liens, 120 tâches et 11 services
  valides. `uv run python scripts/scan_secrets.py` : self-test du détecteur et
  128 fichiers passent. `git diff --check` sans erreur.
- L'intégration Auth réelle, PostgreSQL/Redis et les contrôles navigateur sont
  suivis dans la CI de la PR. Aucune réussite locale de ces tests n'est revendiquée
  avec Docker arrêté. Le warning TestClient/httpx existant est inchangé.

## Recette distante du code

Sur `cc719a8`, les quatre jobs du [push](https://github.com/ABDOUUisHERE/ai-property-management-saas/actions/runs/43015087560)
et les quatre jobs de la [PR](https://github.com/ABDOUUisHERE/ai-property-management-saas/actions/runs/43015158380)
ont réussi. Le job infrastructure exécute le test Auth/Mailpit réel, la suite
PostgreSQL/Redis avec récupération après perte du broker, le smoke de l'application
et les parcours navigateur : **121 tests réussis** (92 backend, 17 outillage,
9 frontend, 3 navigateur). Les preuves restent attachées à ce SHA ; la CI du
HEAD documentaire est également suivie sur la PR.

## Incrément suivant — Persistance et façade Auth

Le commit `8f8262c` ajoute migration `0002_identity`, repository et service de
session. `users` lie immuablement le sujet à un profil ; `auth_sessions` stocke
uniquement le hash du cookie opaque, les jetons chiffrés et l'état de renouvellement.
Les politiques RLS ciblent le sujet vérifié ou la capacité exacte de session,
sans organisation fictive ni bypass global. Runtime et propriétaire de migration
sont testés sous RLS forcée ; le dispatcher ne peut lire ces tables.

La durée absolue est de 24 h par défaut, bornée à 7 jours et immuable pour le rôle
runtime. Un lease de 30 s et une version coordonnent le refresh, sans connexion
SQL pendant le réseau. Un concurrent reçoit `session_busy` ; un lease expiré ou
un refresh ambigu impose un login. Logout commit la révocation et l'effacement
du ciphertext avant l'appel fournisseur ; sa réponse tardive ne peut réactiver
la session. La signature du JWT stocké est vérifiée avant résolution, puis l'état
local est relu. Une panne JWKS seule bloque l'accès sans effacer la session.

La façade expose register/login/me/refresh/logout et un endpoint CSRF. Elle
applique Origin, CSRF signé lié au cookie, CORS restrictif, `no-store`, corps
bornés et limites Redis atomiques par source et email hachés. Les seuls secrets
créés en local sont dans `.env` ignoré, jamais dans Git ; les workers, dispatcher
et processus de migration ne reçoivent pas les clés navigateur.

Commandes exécutées le 2026-11-11 :

- `uv run python scripts/dev.py up` : dix processus healthy et migration terminée.
- `uv run python scripts/dev.py smoke` : PostgreSQL, Auth/Mailpit, Redis et S3 réussis.
- `uv run python scripts/application.py test --broker-recovery` : **149 tests
  backend réussis**, aucune exclusion, dont le parcours HTTP Auth réel et les
  courses refresh/logout, rotation, rollback, pool et refus SQL.
- `uv run python scripts/application.py smoke` : UI/proxy/API et reçu outbox réel réussis.
- Ruff, mypy strict (27 fichiers), contrat OpenAPI, typage, lint, format, neuf
  tests frontend et build réussis. `npm run check:api` ne produit plus de diff
  après régénération et commit du client.
- `uv run pytest` à la racine : **19 tests d'outillage réussis**. `npm run test:e2e` :
  **3 parcours navigateur réussis** (shell/proxy, clavier/dialogue et mobile).
  Total local distinct : **180 tests réussis**. La CI du HEAD final est suivie sur la PR.

Le downgrade `0002_identity` supprime profils et sessions : testé uniquement dans
la base jetable, jamais sur la base de développement. Voir le runbook pour la
restauration et la rotation des clés. Le warning TestClient/httpx existant demeure.

Prochain lot autorisé dans P03 : T023 récupération de compte, puis organisations,
invitations, RBAC et écrans Auth. La fusion de ce lot attend un accord couvrant
l'action ; P04 attend un nouvel accord.
