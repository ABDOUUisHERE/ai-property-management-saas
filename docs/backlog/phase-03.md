# E03 — Identités et entreprises

Phase de chaque tâche : **P03**. Version : **MVP**. Gate : P02 vérifiée, accord et D01/D02/D05 validées.

## FEA07 — Authentification unique

### US07 — Comme utilisateur, je veux créer et protéger ma session sans second compte de credentials.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T020 — Profil et adapter Auth | Relier utilisateur métier au sujet Supabase et exposer register/login/me | identity | P0 | T012, T015, T005 | Sujet unique, identité vérifiée, profil créé de façon récupérable, pas de mot de passe métier | Succès/échec Auth, création profil répétée, sujet étranger et fournisseur indisponible | 5 |
| T021 — Vérification et cycle de session | Valider JWT fournisseur et gérer session opaque de façade | identity | P0 | T020 | Claims vérifiés, tokens chiffrés côté serveur, révocation locale immédiate et renouvellements coordonnés | Token falsifié/expiré, mauvais issuer/aud, rotation de clés, refresh concurrent, timeout et logout | 8 |
| T022 — Transport et protection Auth | Implémenter cookies, CSRF, Origin/CORS et limites de débit | identity/security | P0 | T021 | Cookies adaptés à HTTPS/local, mutations protégées, pas de token navigateur persistant | CSRF login/logout/mutation, origine refusée, cookie flags, throttling | 5 |
| T023 — Récupération de compte | Ajouter demande et confirmation reset via fournisseur | identity | P0 | T022 | Réponse non énumérante, token expirant et usage unique, redirection allowlistée | Email local, token expiré/réutilisé, compte inconnu, changement de session | 3 |

## FEA08 — Organisations et membership

### US08 — Comme owner, je veux constituer mon équipe et gérer ses droits sans perdre le contrôle de l'entreprise.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T024 — Organisation et premier owner | Créer organisation/membership atomiquement et lister ses organisations | organizations | P0 | T020, T011 | Bootstrap sans bypass global, unicité membership, sélecteur vérifié | Création répétée/concurrente, rollback et liste A/B | 5 |
| T025 — Invitations d'équipe | Inviter avec email local asynchrone, accepter et révoquer | organizations | P1 | T024, T019 | Jeton haché, expiration, usage unique, destinataire vérifié et rôle autorisé ; port email minimal réutilisable en P07 | Réception Mailpit, acceptation concurrente, mauvais email, expiration et révocation | 5 |
| T026 — Cycle des membres | Changer rôle, retirer membre, transférer ownership | organizations | P0 | T024 | Au moins un owner, effet immédiat des permissions, tâches orphelines signalées par contrat | Retrait/déclassement simultané des owners, élévation interdite, session déjà ouverte | 5 |

## FEA09 — Isolation et politiques d'accès

### US09 — Comme entreprise, je veux que mes données restent inaccessibles à toute autre organisation.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T027 — RLS et intégrité tenant | Poser politiques, FK composites et droits DB runtime | organizations/database | P0 | T024, T012 | Contexte absent refusé, INSERT/UPDATE contrôlés, rôle sans bypass et bootstrap borné | SQL direct runtime, référence étrangère, mutation organization_id, migration/owner | 8 |
| T028 — Résolution du tenant | Construire TenantContext après identité et membership actuelle | organizations/security | P0 | T027, T021 | Sélecteur client non probant, transaction scoped, plusieurs onglets possibles | Header falsifié, membre retiré, pool A→B, absence contexte et jobs | 5 |
| T029 — Audit sensible | Persister audit minimal dans transaction métier | audit | P0 | T027, T019 | Rôle/invitation/organisation audités, lecture contrôlée, contenu expurgé | Rollback, accès A/B, contenu secret absent et acteur retiré | 3 |
| T030 — RBAC ressource/action | Implémenter matrice et politique 403/404 | organizations/security | P0 | T026, T028, T029 | Owner/manager/staff contrôlés serveur, refus cohérents | Matrice autorisations/refus, ID étranger, champs de rôle injectés | 5 |

## FEA10 — Parcours identité et recette

### US10 — Comme membre de plusieurs organisations, je veux changer de contexte sans mélanger les données.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T031 — Écrans Auth | Créer inscription/login/reset et retours de session | frontend/identity | P1 | T017, T023 | États accessibles, aucune fuite d'information, session expirée traitée | RTL formulaires/erreurs/clavier, Playwright connexion et reset local | 3 |
| T032 — Sélection d'organisation | Implémenter navigation et invalidation du cache par tenant | frontend/organizations | P0 | T031, T028 | Cache et requêtes précédentes retirés, deux onglets indépendants | Réponse tardive A après sélection B, logout, utilisateur multi-tenant | 5 |
| T033 — Gestion des membres UI | Exposer invitations/rôles et garde-fous ownership | frontend/organizations | P1 | T025, T026, T030, T032 | Actions selon rôle, confirmations et erreurs accessibles | RTL/Playwright invitation, retrait dernier owner et accès staff refusé | 3 |
| T034 — Recette identité/isolation | Consolider fixtures A/B, E2E auth et contrôles CI | quality | P0 | T018, T022, T027, T030, T033 | Tests PostgreSQL runtime/API et E2E auth verts, aucun accès croisé | Matrice A/B, réutilisation pool, rôles retirés, CSRF et E2E en CI | 5 |
