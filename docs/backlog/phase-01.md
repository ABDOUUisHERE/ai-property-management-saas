# E01 — Environnement et organisation

Phase de chaque tâche : **P01**. Version : **MVP**. Gate : validation du cadrage et D01/D12 ; les actions distantes exigent une autorisation explicite.

## FEA01 — Conventions de projet

### US01 — Comme contributeur, je veux un cadre de travail clair pour livrer des changements vérifiables.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T001 — Conventions et documentation initiale | Finaliser README, règles Codex, contribution et décisions validées | docs | P1 | — | Statuts proposés/acceptés explicites, commandes non inventées, CONTRIBUTING cohérent | Liens locaux, cohérence avec cadrage approuvé | 2 |
| T002 — Initialisation Git locale | Initialiser main après accord, vérifier identité et exclusions | tooling | P1 | T001 | `.git` autonome, identité vérifiée, secrets/cache ignorés ; aucune publication implicite | `git status`, vérification fichiers suivis et identité, scan secret | 2 |
| T003 — Dépôt et jalons GitHub autorisés | Préparer puis créer origin/milestones/Project si autorisés | workflow | P1 | T002 | Nom/visibilité/licence choisis, URLs vérifiées, indisponibilité Project documentée | Lire dépôt distant et jalons créés ; refus d'accès rapporté | 3 |

## FEA02 — Pilotage du backlog

### US02 — Comme lead, je veux relier chaque livraison à un besoin et à une preuve.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T004 — Issues et workflow validés | Publier le backlog approuvé et configurer branches/PR lorsque autorisé | workflow | P1 | T003 | IDs, critères, dépendances, milestones et URLs réelles ; aucune duplication | Comparaison backlog/Issues, liens et droits, essai template PR | 3 |

## FEA03 — Environnement reproductible

### US03 — Comme développeur, je veux démarrer et vérifier les dépendances sans données réelles.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T005 — Faisabilité Auth locale | Vérifier composition Supabase Auth, clés et mails sur la cible Docker | identity/infra | P0 | T002 | Choix D01 éprouvé, images épinglées et besoins mémoire relevés ; réviser ADR si échec | Démarrage Auth, inscription/login/clé attendue, email local | 5 |
| T006 — Compose des dépendances | Assembler PostgreSQL métier, Redis, Auth, stockage objet et Mailpit | infra | P0 | T005 | Commande racine unique, healthchecks, réseaux/volumes, ports locaux bornés | Démarrage neuf, redémarrage, panne d'un service et readiness | 5 |
| T007 — Configuration et lockfiles | Définir environnements, exemples sans secrets et outils verrouillés | tooling/config | P0 | T006 | Versions compatibles choisies, `.env.example`, validation config et exclusions | Installation depuis lockfiles, secret absent, scan fichiers | 3 |
| T008 — Recette bootstrap dépendances | Documenter démarrage reproductible sans compte cloud obligatoire | infra | P0 | T007 | Sur environnement neuf, dépendances démarrent ; prérequis Docker/Windows explicites | Rejouer `docker compose up --build` puis redémarrage, preuve archivée | 3 |
| T009 — CI minimale | Créer pipeline initial de contrôle docs/config et secrets | ci | P1 | T007 | Workflow réel sans jobs applicatifs factices, permissions minimales ; publication selon autorisation | Validation YAML, contrôle liens et détection d'un secret de fixture | 2 |
