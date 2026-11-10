# Cahier des charges — AI-Powered Property Management SaaS

**Version :** 1.0 — projet autonome, démarrage de zéro  
**Destinataire :** Codex, agent de développement  
**Objectif :** construire un SaaS multi-tenant exploitable en démonstration, sans dépendance à un autre projet.

## 1. Mission produit
Créer une plateforme de gestion de locations de courte durée permettant à plusieurs entreprises indépendantes de gérer leurs biens, voyageurs, réservations, disponibilités, paiements, équipes, tâches de ménage et tableaux de bord. Les données d'une entreprise ne doivent jamais être accessibles à une autre.

**Personas :** propriétaire d'organisation, gestionnaire, agent opérationnel, voyageur (accès restreint).  
**Hors périmètre initial :** intégrations officielles Airbnb/Booking.com sans accès partenaire, système de serrure connectée réelle, moteur de tarification ML avancé, comptabilité réglementaire.

## 2. Stack obligatoire
- Backend : Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, uv ou Poetry.
- Frontend : React, TypeScript, Vite, TanStack Query, React Router, bibliothèque de composants accessible.
- Données : PostgreSQL (Supabase PostgreSQL possible), Redis pour cache et tâches ; stockage objet S3-compatible pour images.
- Authentification : Supabase Auth **ou** JWT sécurisé côté serveur ; choisir une seule source de vérité et documenter le choix.
- Paiements : Stripe en mode test, Checkout et webhooks signés.
- Infrastructure : Docker Compose en local, AWS pour déploiement optionnel (ECS/Fargate ou App Runner, RDS, S3) ; GitHub Actions.
- Tests : pytest, httpx, Testcontainers ou base PostgreSQL dédiée ; Vitest/React Testing Library, Playwright pour parcours critiques.
- Observabilité : logs structurés, health checks, métriques basiques et suivi d'erreurs.

## 3. Architecture
Monolithe modulaire FastAPI (éviter des microservices prématurés). Modules : identity, organizations, properties, guests, reservations, availability, pricing, payments, operations, notifications, reporting, audit. Chaque module expose routers, schemas, services, repositories et modèles selon ses besoins. Ne pas mélanger les règles métier dans les routes HTTP. Contrats OpenAPI versionnés sous `/api/v1`. Migrations Alembic versionnées. Toute requête métier est contextualisée par `tenant_id` dérivé d'une identité authentifiée, jamais accepté comme preuve d'autorisation depuis un paramètre fourni par le client. Si Supabase RLS est utilisé, le tester explicitement ; l'isolation applicative reste obligatoire.

## 4. Fonctionnalités et règles métier
### F01 — Identité et organisations (MVP)
- Inscription, connexion, déconnexion, récupération de mot de passe.
- Création d'une organisation et invitation d'utilisateurs.
- Rôles : owner, manager, staff ; permissions sur chaque ressource.
- Changement d'organisation pour les utilisateurs membres de plusieurs tenants.
- Journal d'audit pour modifications sensibles.

### F02 — Propriétés et unités (MVP)
- CRUD propriétés : nom, adresse, fuseau horaire IANA, devise, capacité, équipements, photos, statut.
- Une propriété peut avoir une ou plusieurs unités louables.
- Gestion de l'archivage ; interdiction de suppression destructrice d'une unité ayant des réservations historiques.

### F03 — Voyageurs (MVP)
- Fiches voyageurs : nom, email, téléphone facultatif, préférences et historique.
- Données personnelles minimisées, masquées selon rôle ; suppression/anonymisation lorsque juridiquement possible.

### F04 — Réservations et disponibilités (MVP critique)
- Réservations : draft, pending, confirmed, checked_in, checked_out, cancelled ; transitions validées.
- Dates `check_in` inclusif, `check_out` exclusif ; timezone locale pour l'affichage, stockage UTC pour les instants.
- Calendrier par unité et organisation ; blocages manuels pour maintenance.
- **Aucune double réservation confirmée** : contrainte PostgreSQL d'exclusion sur plage de dates et unité, dans une transaction ; tests de concurrence réels.
- Réservation atomique et idempotente avec clé d'idempotence pour les appels de création.
- Prix détaillé : nuitées, frais, taxes paramétrables, remise, total ; montants en unités mineures et code ISO de devise.

### F05 — Paiements Stripe (MVP)
- Création de session Checkout en mode test depuis une réservation autorisée.
- Webhook Stripe avec vérification cryptographique de signature, déduplication par event ID, persistance de l'événement et traitement idempotent.
- États payment_pending, paid, failed, refunded ; ne jamais considérer un redirect navigateur comme preuve de paiement.
- Remboursement manuel réservé aux rôles autorisés avec journal d'audit.
- Aucune donnée de carte bancaire stockée dans l'application.

### F06 — Opérations de nettoyage et maintenance (MVP)
- À la confirmation ou au checkout, générer une tâche de ménage selon règles configurées, sans doublon.
- CRUD tâches, attribution à staff, échéance, priorités, statuts, notes.
- Signalement de maintenance, photos et historique d'interventions.
- Notifications email simulables localement ; envoi asynchrone avec retry et dead-letter ou file d'échecs consultable.

### F07 — Tarification (V2)
- Prix de base, tarifs par jour de semaine, saison, minimum de séjour et remises.
- Simulation d'un devis avant réservation ; calcul déterministe, tests de frontières.
- Pas de promesse de « dynamic AI pricing » sans modèle et données vérifiables.

### F08 — Reporting (MVP)
- Dashboard : réservations par statut, taux d'occupation, revenu brut, ADR et RevPAR, avec définitions documentées.
- Filtres dates/propriété/unité et export CSV.
- Données toujours limitées au tenant actif.

### F09 — Intégrations de canaux (V2)
- Interface `ChannelAdapter` indépendante du fournisseur ; simulateur local pour événements de réservation externes.
- Import/export iCalendar si adapté, avec limites clairement documentées (synchronisation non instantanée).
- Webhooks entrants signés lorsqu'un fournisseur le permet ; retry, déduplication, traitement hors ordre.
- Ne jamais prétendre intégrer Airbnb/Hostaway en production sans accès API autorisé.

### F10 — IA optionnelle (V3)
- Assistant interne de recherche sur les données d'exploitation avec outils en lecture seule, contrôle d'accès et validation humaine pour actions sensibles. Cette fonctionnalité n'est pas nécessaire au MVP.

## 5. Modèle de données minimal
`organizations`, `users`, `memberships`, `properties`, `units`, `guests`, `reservations`, `availability_blocks`, `rate_rules`, `payment_records`, `webhook_events`, `tasks`, `maintenance_tickets`, `notifications`, `audit_events`, `idempotency_keys`.  
Chaque table métier porte `organization_id` ; indexer les recherches courantes ; clés étrangères et contraintes CHECK. `reservations` inclut unit_id, guest_id, start_date, end_date, status, total_minor, currency. Définir explicitement les règles de suppression et conservation.

## 6. API attendue (exemples)
- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/me`
- `POST /api/v1/organizations`, `GET /api/v1/organizations/{id}/members`
- `GET|POST /api/v1/properties`, `GET|PATCH /api/v1/properties/{id}`
- `GET|POST /api/v1/units`, `GET /api/v1/units/{id}/calendar`
- `GET|POST /api/v1/guests`
- `GET|POST /api/v1/reservations`, `POST /api/v1/reservations/{id}/confirm`, `POST /api/v1/reservations/{id}/cancel`
- `POST /api/v1/payments/checkout`, `POST /api/v1/webhooks/stripe`
- `GET|POST /api/v1/tasks`, `PATCH /api/v1/tasks/{id}`
- `GET /api/v1/reports/overview`, `GET /health/live`, `GET /health/ready`
Documenter schémas, codes HTTP, pagination, filtres et erreurs normalisées. Ne pas générer automatiquement des endpoints non nécessaires.

## 7. Interface utilisateur
Pages : connexion/inscription, sélection organisation, dashboard, liste et détail propriétés, calendrier des réservations, création réservation, voyageurs, paiements, opérations, reporting, paramètres/membres. Responsive desktop-first, états loading/empty/error, navigation clavier, feedback accessible, confirmation des actions destructives. Utiliser des données de démonstration réalistes mais fictives.

## 8. Sécurité et fiabilité
- Contrôle tenant et RBAC sur **chaque** endpoint et accès DB ; tests de tentatives cross-tenant.
- Validation Pydantic, limitation de débit sur auth/webhooks, CORS restrictif, secrets par variables d'environnement, aucun secret commité.
- Protection CSRF si authentification par cookies ; cookies Secure/HttpOnly/SameSite.
- Transactions atomiques, timeouts, retry avec backoff uniquement pour opérations sûres, files d'échecs.
- Journalisation sans mots de passe, tokens, données bancaires ni messages sensibles.
- Sauvegarde/restauration documentée ; migration réversible lorsque raisonnable.

## 9. Tests et critères d'acceptation
1. Deux tenants créés : un membre A ne peut jamais lire/modifier une ressource B (403/404 selon politique documentée).
2. Deux créations concurrentes sur même unité et dates : au plus une réservation confirmée.
3. Checkout et webhook Stripe de test : état payé uniquement après webhook signé ; événement répété traité une fois.
4. Checkout déclenche une seule tâche de ménage malgré événements répétés.
5. Calendrier respecte blocages et dates de checkout exclusives.
6. Dashboard et export n'affichent aucune donnée d'un autre tenant.
7. `docker compose up --build` démarre localement ; migrations et seed reproductibles.
8. CI exécute lint, typage, tests backend/frontend et au moins 3 scénarios E2E (auth, réservation, opérations).
9. README contient architecture, décisions, commandes, captures, démo, limites et API docs.

## 10. Plan de livraison Codex
- **Phase 0 — Cadrage :** initialiser repo, ADRs, backlog, conventions, Docker, CI minimale ; aucune fonctionnalité fictivement déclarée.
- **Phase 1 — Fondations :** FastAPI, React, PostgreSQL, Alembic, auth, organisations, RBAC, isolation et tests.
- **Phase 2 — Cœur métier :** propriétés, unités, voyageurs, disponibilité et réservations concurrent-safe.
- **Phase 3 — Paiements :** Stripe test, webhooks signés, idempotence, historique.
- **Phase 4 — Opérations :** tâches, maintenance, notifications et workers.
- **Phase 5 — Reporting et UX :** dashboards, filtres, exports, E2E, accessibilité.
- **Phase 6 — Production-readiness :** sécurité, observabilité, documentation, déploiement AWS si credentials disponibles.
- **Phase 7 — Extensions facultatives :** règles tarifaires, adaptateurs de canaux, assistant IA interne.

Chaque phase : plan court → implémentation → migrations → tests → vérification → résumé des fichiers modifiés, commandes et limites. **Ne pas avancer si la phase courante échoue.**

## 11. Livrables finaux
Dépôt GitHub autonome, README, `.env.example`, Docker Compose, migrations, OpenAPI, données seed, scripts de test, GitHub Actions, architecture diagram, captures ou vidéo démo, procédure de déploiement, backlog des améliorations.

## 12. Prompt initial à coller dans Codex
> Tu développes depuis zéro le projet décrit dans `01_property_management_saas_independent.md`. Ce dépôt est totalement indépendant. Commence uniquement par la phase 0 : propose une architecture modulaire simple, une arborescence, les ADRs et le backlog ; crée ensuite le squelette exécutable avec Docker Compose et CI minimale. N'invente aucun résultat de test ni intégration. Demande des credentials seulement lorsqu'ils deviennent indispensables ; privilégie les modes test et simulateurs. Après chaque phase, fournis les commandes exactes de validation et attends mon accord avant la suivante.


## GitHub, qualité du dépôt et contributions quotidiennes — exigences obligatoires

Ce projet démarre **de zéro** dans son propre dépôt GitHub, indépendant de tout autre projet. Dès la phase 0, Codex doit initialiser Git, créer un dépôt distant via `gh` si l'accès est configuré (sinon demander à l'utilisateur de créer le dépôt), configurer `origin`, et vérifier que l'identité Git et l'e-mail de commit sont associés au compte GitHub de l'utilisateur. Ne jamais inventer un dépôt ni prétendre avoir poussé sans vérification.

### Organisation du dépôt
- Répertoire racine propre, `README.md` expliquant produit, installation, architecture, tests, captures, limites et démonstration ; `AGENTS.md` donnant les règles à Codex ; `CONTRIBUTING.md`, `.gitignore`, `.env.example`, `LICENSE` si choisie.
- Code séparé en `backend/`, `frontend/`, `infra/`, `docs/`, `.github/workflows/` ; tests à proximité des composants ou dans des répertoires dédiés cohérents.
- Documentation `docs/architecture/`, `docs/adr/`, `docs/api/` et `docs/runbooks/` ; ADR pour les décisions techniques importantes. Pas de fichiers ou de couches inutiles créés seulement pour paraître complexes.
- CI GitHub Actions sur chaque PR : lint, format, vérification de types, tests backend/frontend, build ; intégration PostgreSQL et contrôles de sécurité adaptés. Aucun secret dans Git, dans les logs ou dans les PR.

### Workflow de livraison
1. Décomposer chaque phase en GitHub Issues petites et vérifiables, avec objectif, tâches, critères d'acceptation et dépendances.
2. Utiliser une branche par changement (`feat/...`, `fix/...`, `test/...`, `docs/...`, `refactor/...`) à partir de `main` à jour.
3. Réaliser des commits atomiques et utiles en Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`) ; tester avant de committer.
4. Ouvrir une PR par lot cohérent, liée à son Issue, avec résumé, preuves de tests et captures si UI ; fusionner après CI verte et revue (humaine si disponible, sinon auto-revue explicite).
5. Garder `main` stable ; utiliser des tags de versions pour les jalons MVP et des releases avec changelog.
6. À la fin de chaque séance, fournir un bilan chiffré par type de contribution, en distinguant l’activité effectuée des contributions visibles sur le profil GitHub : Issues closes, PR merged, commits utiles, tests, liens GitHub vérifiés, problèmes restants et prochain lot.

### Contributions visibles, sans manipulation
- Chercher à produire régulièrement plusieurs contributions **authentiques** par journée active : petites fonctionnalités, tests, correctifs, documentation technique et PR significatives. L’utilisateur souhaite viser **50 à 100 contributions GitHub par jour actif** comme objectif ambitieux de visibilité. Cet objectif est **indicatif et subordonné au travail réel**, jamais un quota de commits. Mesurer séparément commits significatifs, Issues, PR et contributions effectivement affichées par GitHub ; ne pas supposer qu’une action égale une contribution comptabilisée. Si 50 contributions authentiques ne sont pas justifiées par le travail du jour, annoncer le nombre réel sans fabriquer d’activité.
- Ne jamais fractionner artificiellement un changement, générer des commits vides, modifier des dates de commit, gonfler les statistiques ou sacrifier la qualité pour le graphique GitHub.
- Vérifier les règles d'affichage GitHub : e-mail lié au compte, commits sur la branche par défaut ou `gh-pages` (ou fusionnés sur la branche par défaut selon le mode de merge), contributions privées selon réglages, et PR/Issues pouvant aussi compter. Les commits sur des branches non fusionnées ne sont pas nécessairement visibles dans le graphe.
- Codex ne doit pas créer de PR, pousser, fusionner ou modifier la configuration distante sans l'autorisation et les accès nécessaires. Documenter ce qui est réellement effectué.

### Consigne permanente pour Codex
**Avant toute implémentation**, proposer une Issue et un plan minimal. **Pendant l'implémentation**, travailler par petits incréments testés et commits significatifs. **Après l'implémentation**, ouvrir une PR si autorisé, vérifier la CI, présenter les preuves et attendre l'accord de l'utilisateur avant de commencer la phase suivante. Ne pas ajouter une dépendance au second projet.
