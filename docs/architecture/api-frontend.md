# API, frontend et arborescence proposés

## Contrats API

API-first : stabiliser les schémas Pydantic et exemples avant chaque tranche ; OpenAPI généré et contrôlé dans la CI. `/api/v1` pour le métier ; sondes hors version. Schemas d'entrée distincts des modèles ORM, refus des champs sensibles injectés (`organization_id`, rôle, total, état financier).

| Zone | Contrats proposés | Contraintes |
| --- | --- | --- |
| Identité | POST `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/refresh`, `/auth/password-reset/request`, `/auth/password-reset/complete` ; GET `/me` | Façade Auth unique, réponses anti-énumération, cookies/CSRF selon D01 |
| Organisations | POST/GET `/organizations` ; GET `/organizations/{id}/members` ; POST invitations ; acceptation/révocation ; changement de rôle | Vérifier membership réelle pour `{id}`, protéger dernier owner |
| Biens | GET/POST `/properties`, GET/PATCH `/properties/{id}` ; GET/POST `/units`, GET/PATCH `/units/{id}` ; commandes d'archivage et photos | CRUD soumis aux droits et à l'historique |
| Voyageurs | GET/POST `/guests`, GET/PATCH `/guests/{id}`, GET historique ; commande d'anonymisation | Vue selon rôle, conservation contrôlée |
| Calendrier | GET `/units/{id}/calendar` et calendrier organisation filtré ; POST/PATCH/annulation blocages | Période bornée, unité du tenant, protocole de lock |
| Devis et séjours | POST `/quotes` ; GET/POST `/reservations`, GET/PATCH `/reservations/{id}` ; POST `/{id}/confirm`, `/cancel`, `/check-in`, `/check-out` | Clé d'idempotence création, transitions dédiées, PATCH limité |
| Paiements | POST `/payments/checkout` ; GET paiements autorisés ; POST `/payments/{id}/refund` ; GET statut remboursement | Réservation du tenant, mode test, owner pour remboursement proposé |
| Stripe | POST `/webhooks/stripe` | Authentification fournisseur par signature, corps brut ; pas de session utilisateur ni CSRF navigateur |
| Opérations | GET/POST `/tasks`, PATCH `/tasks/{id}` ; tickets maintenance et pièces jointes ; paramètres de génération | Staff borné à son périmètre, clés métier uniques |
| Notifications | Lecture statut/échecs selon rôle ; commande de reprise autorisée | Pas d'endpoint d'envoi arbitraire |
| Reporting / audit | GET `/reports/overview`, `/reports/export`, `/audit-events` | RBAC, période/volume bornés, export expurgé et tenant |
| Sondes | GET `/health/live`, `/health/ready` | Pas de détails internes exposés ; dépendances nécessaires seulement |

Il s'agit d'un inventaire de contrats, pas d'endpoints à générer tous immédiatement. Créer chaque route avec sa tâche et ses critères. Le sélecteur tenant proposé est `X-Organization-ID` pour le métier ; le serveur le résout par l'identité et les memberships, puis ignore tout `organization_id` fourni comme autorité. Les routes sans tenant actif ont leur politique ciblée explicite.

Proposition de conventions : 201 création, 200 commande idempotente déjà appliquée/lecture, 204 sans contenu, 400 entrée invalide hors validation, 401 session, 403 permission, 404 ressource invisible, 409 état/inventaire/idempotence/version, 422 validation de schéma, 429 débit, 503 dépendance indisponible. Documenter 409 et les reprises, pas de retry automatique des mutations sans clé stable.

Erreurs inspirées Problem Details : `type`, `title`, `status`, `detail` expurgé, `instance`, `code` stable, `request_id`, et violations de champs autorisées. Dates ISO, instants UTC avec offset explicite, monnaie `{amount_minor,currency}`. Pagination initiale page/limit, tri stable avec identifiant en départage ; limite par défaut 25, maximum 100 proposé. Calendriers bornés à 366 jours et exports limités/configurables ; prévoir traitement asynchrone seulement si nécessaire. Ne pas exposer un total global ignorant RLS.

## Frontend

React + TypeScript strict + Vite ; React Router pour navigation, TanStack Query pour l'état serveur, bibliothèque accessible à choisir en T016 après vérification de compatibilité. Formulaires avec validation client complémentaire, l'API restant autorité. Types client générés depuis OpenAPI, sans entités ORM copiées à la main. Les règles monétaires et d'autorisation ne sont pas dupliquées dans le navigateur.

Organisation par features reflétant les usages ; `shared/` pour composants réellement réutilisés, `app/` pour bootstrap/providers/routes. Les pages composent les features, les hooks encapsulent les appels. État local React pour dialogues et filtres ; pas de store global général tant que le besoin n'existe pas.

| Parcours | Écrans | États et preuve attendus |
| --- | --- | --- |
| Connexion et organisations | Inscription, login, récupération, sélection/paramètres/membres | Erreurs accessibles, invitation, session expirée, changement tenant sans fuite |
| Biens | Liste/détail propriétés et unités, photos, archivage | Loading/empty/error, validations, confirmation destructive |
| Séjours | Calendrier par unité/organisation, voyageurs, devis et création | Date exclusive visible, conflit 409 expliqué, double clic stable |
| Paiements | Statut, ouverture Checkout test, retour en attente, historique, remboursement | Aucun succès avant preuve serveur, affichage anomalie et refus de rôle |
| Opérations | Tâches assignées, suivi ménage, tickets et photos | Navigation clavier, échec réseau, permissions staff |
| Dashboard et reporting | Cartes, filtres dates/propriété/unité, CSV | Définitions/monnaies visibles, données autorisées seulement |

Les Query keys incluent le tenant ; annuler les requêtes en vol et retirer le cache lors d'un changement d'organisation/déconnexion. Une réponse ancienne ne doit pas remplir l'écran du nouveau tenant. Chaque requête capture le tenant sélectionné au départ ; pas de variable globale mutable injectée tardivement. Une route masquée n'est pas une mesure d'autorisation.

Desktop-first responsive ; navigation clavier, labels, focus de dialogue, retour d'erreur lié au champ et annonces de statut. Objectif d'accessibilité proposé : WCAG 2.2 AA pour les parcours critiques, vérifications automatiques et manuelles. Données fictives et devise/fuseau explicités dans la démo.

## Arborescence cible

Cette arborescence est un **plan** ; seuls les documents sont créés maintenant. Les dossiers/modules apparaissent lorsqu'une tâche les utilise.

```text
/
├── README.md
├── AGENTS.md
├── GLOSSARY.md
├── property_management_saas_cahier_des_charges.md
├── CONTRIBUTING.md                  # phase 1
├── LICENSE                          # après choix utilisateur
├── .gitignore
├── .env.example                     # noms/valeurs fictives seulement
├── compose.yaml
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── migrations/versions/
│   ├── src/app/
│   │   ├── main.py
│   │   ├── bootstrap.py             # assemblage et injection
│   │   ├── core/                    # config, DB, HTTP, sécurité technique
│   │   ├── modules/
│   │   │   ├── identity/
│   │   │   ├── organizations/
│   │   │   ├── properties/
│   │   │   ├── guests/
│   │   │   ├── availability/
│   │   │   ├── pricing/
│   │   │   ├── reservations/
│   │   │   ├── payments/
│   │   │   ├── operations/
│   │   │   ├── notifications/
│   │   │   ├── reporting/
│   │   │   └── audit/
│   │   └── workers/                 # entrypoints et dispatcher communs
│   └── tests/{unit,integration,contract}/
├── frontend/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── src/
│   │   ├── app/{router,providers}/
│   │   ├── features/                # modules UI et tests à proximité
│   │   ├── pages/
│   │   ├── shared/{ui,api,lib}/
│   │   └── generated/               # types issus d'OpenAPI
│   └── e2e/
├── infra/
│   ├── docker/                      # images/proxy et Auth local épinglé
│   └── aws/                         # IaC après validation option AWS
├── scripts/                         # uniquement commandes réellement utiles
├── .github/
│   ├── workflows/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
└── docs/
    ├── architecture/
    ├── adr/
    ├── backlog/
    ├── api/                         # contrats et snapshots après phase 2
    ├── runbooks/                    # exploitation après preuves réelles
    ├── github-workflow.md
    └── roadmap.md
```

Dans un module simple : `router.py`, `schemas.py`, `service.py`, `repository.py`, `models.py` selon besoin. Dans reservations/payments : sous-dossiers `domain/`, `application/`, `infrastructure/`, `api/` si leur complexité le justifie. Le domaine pur n'importe ni FastAPI, ni SDK Stripe, ni session SQLAlchemy. Les types transversaux se limitent aux contrats nécessaires (acteur/tenant, monnaie, horloge, unité de travail).
