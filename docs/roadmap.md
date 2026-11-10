# Roadmap progressive proposée

Date : 2026-11-10. Plan par livrables et portes de validation, sans calendrier inventé. Les complexités du backlog sont relatives ; estimer une durée après le premier incrément mesuré et selon la disponibilité réelle de l'équipe.

## Session de cadrage — clôturée et validée le 2026-11-10

Livrables : analyse intégrale, architecture, modèle métier, ADRs proposés, risques, backlog, roadmap, organisation GitHub proposée, README d'état et règles Codex. Aucune fonctionnalité métier, aucun squelette applicatif, aucune configuration Docker/CI ni action Git distante n'est réalisée dans cette session. Vérification des documents et de leurs références avant remise.

Sortie obtenue : l'utilisateur a validé le périmètre, les recommandations et le backlog (« je valide »). P01 commence ; chaque phase suivante garde sa porte d'accord. La publication distante et le déploiement AWS n'ont pas été autorisés par cette validation de cadrage.

## Correspondance avec le cahier des charges

Les neuf phases demandées dans la session sont le calendrier opérationnel de référence ; elles affinent les phases 0–7 de la spécification.

| Roadmap de session | Phase du cahier des charges | Objet |
| --- | --- | --- |
| Analyse actuelle | Partie documentaire de phase 0 | Cadrage uniquement |
| P01 | Reste de phase 0 | Git autorisé, environnement et CI minimale |
| P02 | Début phase 1 | Architecture backend/frontend exécutable |
| P03 | Reste phase 1 | Identités, organisations, RBAC/isolation |
| P04 | Début phase 2 | Biens, unités et voyageurs |
| P05 | Reste phase 2 | Disponibilités, devis et réservations |
| P06 | Phase 3 | Paiements |
| P07 | Phase 4 | Opérations et notifications |
| P08 | Phase 5 | Reporting et UX |
| P09 | Phase 6 | Préparation exploitation, AWS si autorisé |
| PX2 / PX3 | Phase 7 | Extensions V2 / V3 |

## P01 — Initialisation du dépôt et environnement

Backlog : E01, T001–T009. Prérequis : approbation du cadrage, D01 et choix GitHub D12 ; autorisation distincte des actions distantes.

Livrables : conventions de contribution, Git local, exclusions de secrets, outils/versions et lockfiles ; composition Docker des dépendances, configuration d'exemple et Auth local vérifié ; CI minimale. Dépôt distant, milestones et Project seulement lorsque autorisés ; publication d'Issues seulement après validation du backlog.

Condition de sortie : démarrage des dépendances sur environnement neuf, Auth local réellement vérifié, secrets exclus et pipeline initial cohérent. Si GitHub n'est pas autorisé/disponible, tracer les tâches distantes différées et obtenir un accord explicite pour continuer localement ; ne pas les considérer accomplies. L'application métier n'existe pas encore à ce stade.

## P02 — Architecture backend et frontend

Backlog : E02, T010–T019. Prérequis : sortie P01 et accord.

Livrables : FastAPI et React exécutables, DI/configuration, SQLAlchemy/Alembic, erreurs/logs/sondes, OpenAPI, client typé, shell accessible, tests et CI applicative ; primitives outbox/worker. Ajouter les images API/UI au Compose.

Condition de sortie : application et dépendances démarrent via la commande racine, migration de base vide réussie, lint/format/types/tests/builds verts ; commit/rollback/outbox prouvés. Aucun endpoint métier factice ni module vide destiné à donner une impression d'avancement.

## P03 — Authentification, utilisateurs et multi-tenancy

Backlog : E03, T020–T034. Prérequis : sortie P02 et accord ; D01/D02/D05 validées.

Livrables : inscription/login/logout/reset, sessions protégées, organisations/memberships/invitations, RBAC, contexte tenant, RLS/FK composites, audit et interface de changement d'organisation.

Condition de sortie : matrice API et PostgreSQL A/B, absence de contexte et réutilisation du pool prouvées ; CSRF, changement de rôle et dernier owner couverts ; E2E auth et organisation en CI. Aucun développement métier ne passe cette porte avec une isolation encore supposée.

## P04 — Propriétés, unités et voyageurs

Backlog : E04, T035–T046. Prérequis : sortie P03 et accord ; politiques D07/D08 précisées pour les champs concernés.

Livrables : CRUD biens/unités, archivage, stockage privé et photos ; fiches voyageurs et vues masquées/anonymisation ; écrans correspondants et seed fictif. Le modèle d'historique est préparé pour les réservations qui arrivent en P05.

Condition de sortie : CRUD, permissions, contraintes, fichiers privés et vues staff vérifiés ; aucune suppression destructive autorisée par conception. La preuve d'interdiction d'archivage avec réservation réelle sera ajoutée en P05 quand cette table existe, et reste un critère de recette P05.

## P05 — Réservations et prévention du surbooking

Backlog : E05, T047–T060. Prérequis : sortie P04 et accord ; D03/D04/D08 validées.

Livrables : calendrier et maintenance, devis MVP et prix figés, états des séjours, clés d'idempotence, exclusion PostgreSQL, verrou commun par unité, options avec expiration, interface calendrier/réservation. Le port de rapprochement paiement reçoit son adapter Stripe en P06.

Condition de sortie : tests multi-connexions prouvant au plus une confirmation et protection réservation/maintenance ; dates adjacentes, timezone, rollback, idempotence, expiration et archivage avec historique vérifiés ; E2E réservation en CI. Aucun lock Redis ou contrôle du frontend ne tient lieu de garantie DB.

## P06 — Paiements Stripe en mode test

Backlog : E06, T061–T072. Prérequis : sortie P05 et accord ; D04 validée et accès Stripe test à obtenir au moment utile.

Livrables : Checkout autorisé, tentatives récupérables, webhook signé/inbox durable, traitement idempotent/hors ordre, confirmation rapprochée, remboursement autorisé, gestion des succès tardifs, historique et UI.

Condition de sortie : Checkout et webhooks **réels de test** prouvés, fixtures CI pour signature/doublons/ordre, crash et expiration couverts ; aucun paid sur redirect ; anomalie sans double réservation ; remboursement répété sans double restitution. Si accès absents, les tests simulés sont livrables intermédiaires, mais ne clôturent pas la phase.

## P07 — Automatisation des opérations

Backlog : E07, T073–T082. Prérequis : sortie P06 et accord ; D10 validée.

Livrables : règle de ménage, tâches/affectation/statuts/notes, tickets et photos maintenance, emails locaux asynchrones, retry borné et file d'échecs consultable ; écrans staff/manager.

Condition de sortie : événement de départ répété ou rejoué crée une seule tâche ; crash/reprise et panne email vérifiés ; isolation et restrictions staff prouvées ; E2E opérations en CI. Trois scénarios critiques existent désormais : auth, réservation, opérations.

## P08 — Dashboard et reporting

Backlog : E08, T083–T091. Prérequis : sortie P07 et accord ; définitions D08 approuvées.

Livrables : indicateurs définis et exemple chiffré, filtres date/propriété/unité, exports CSV, dashboard accessible, dataset fictif complet et recette locale depuis un environnement neuf.

Condition de sortie : occupation/revenus/ADR/RevPAR comparés à un calcul de référence ; devises séparées ; archivage, maintenance et périodes historiques corrects ; données A/B absentes des agrégats et exports ; Compose/migrations/seed et parcours critiques reproduits.

## P09 — Tests, sécurité, observabilité et préparation AWS

Backlog : E09, T092–T104. Prérequis : sortie P08 et accord ; D07/D11 précisés. Pour AWS, D09, budget et autorisation de provisioning/déploiement.

Livrables : revue des surfaces, expurgation/secrets, scans, métriques/alertes, mesure de charge, sauvegarde et restauration éprouvées, CI complète, accessibilité, runbooks, documentation/captures et recette A01–A09. Option AWS : IaC, staging, migration unique, smoke tests et rollback réel.

Condition de sortie MVP local : toutes les preuves obligatoires A01–A09 disponibles, contrôles verts, restauration locale effectuée, documentation rejouée, risques résiduels explicités et acceptés ; release seulement si autorisée. AWS différé est un statut explicite de livraison, sans prétendre à une validation cloud.

Condition supplémentaire si AWS choisi : T099–T101 terminées avec preuves de staging, réseau/permissions, cookies/HTTPS, jobs/migrations, restauration et rollback ; aucun jalon « AWS déployé » sans vérification de la cible réelle.

## PX2 — Extensions V2

E10/T105–T109 : règles avancées et simulateur de prix, déterminisme et priorité documentée. E11/T110–T115 : ChannelAdapter, simulateur local, iCalendar si pertinent, ingestion fiable et anomalies. Ces deux branches peuvent être développées indépendamment après MVP et validation de leur périmètre.

Sortie de chaque extension : tests spécifiques et non-régression MVP verts, isolation/concurrence conservées, limites de synchro explicitement visibles ; aucune intégration partenaire revendiquée sans accès autorisé et nouvelle recette.

## PX3 — Assistant IA interne facultatif

E12/T116–T120. Prérequis : MVP stable, cas d'usage, données, fournisseur et budget approuvés ; V2 n'est pas un prérequis.

Livrables : outils de lecture tenant/RBAC, réponses référencées, interface et protocole d'évaluation. Aucune action sensible exécutée par le modèle ; les parcours existants restent sous contrôle humain.

Sortie : évaluation pertinence/coût/latence et tentatives d'exfiltration/injection documentées, contrôles de données prouvés, arrêt de l'IA sans impact sur le MVP.

## Rythme de livraison

Pour chaque phase : plan court et Issue proposée → implémentation après accord → migrations → tests → vérification → bilan et accord avant la suivante. Les numéros de tâches servent à la traçabilité, pas à imposer un nombre de commits. Les décisions commerciales et les accès manquants sont remontés au moment où ils bloquent un livrable concret.
