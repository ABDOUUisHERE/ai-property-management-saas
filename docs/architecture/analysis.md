# Analyse du cahier des charges

## Référence, état et ordre de priorité

Lecture intégrale de `property_management_saas_cahier_des_charges.md`, version 1.0, effectuée le 2026-11-10. Le fichier référencé dans son ancien prompt, `01_property_management_saas_independent.md`, n'existe pas ici : utiliser le nom réel. Au démarrage, le workspace ne contient que le cahier des charges et ne possède pas de `.git`.

La demande de cette session restreint la phase initiale aux documents, au backlog, à la roadmap et à `AGENTS.md`. Elle reporte donc le squelette exécutable, Docker, la CI et l'initialisation Git prescrits par le prompt embarqué. Elle interdit toute création distante, push ou Issue avant accord. Cette divergence est résolue par priorité à la demande actuelle, sans modifier le cahier des charges.

## Produit et périmètre

Le produit est un outil B2B pour entreprises de location courte durée, pas une marketplace publique. Le MVP couvre F01–F06 et F08 : identité, entreprises, biens/unités, voyageurs, disponibilités, réservations, prix simples détaillés, Stripe test, ménage, maintenance, notifications et reporting. Les tarifs avancés F07 et les canaux F09 sont V2 ; F10, assistant IA interne, est V3 et facultatif.

Le titre « AI-Powered » ne justifie ni intégration IA anticipée ni promesse de tarification intelligente. Pas de comptabilité réglementaire, serrures réelles, intégration officielle Airbnb/Booking.com sans accès partenaire ni abonnement SaaS/Stripe Connect ajoutés implicitement. L'accès voyageur est ambigu : persona cité, mais rôle et parcours absents. Proposition : fiche voyageur gérée par les équipes au MVP ; portail authentifié ultérieur seulement après validation D06.

## Besoins fonctionnels et dépendances

| Exigence | Résultat attendu | Dépendances principales | Backlog |
| --- | --- | --- | --- |
| F01 | Sessions, organisations, invitations, rôles, changement de tenant, audit | Environnement, contrats, DB et RLS | T020–T034 |
| F02 | Propriétés, unités, photos, archivage préservant les séjours | F01, stockage privé | T035–T042 |
| F03 | Fiches voyageurs, historique, masquage/anonymisation | F01, politique de conservation | T043–T046, T102 |
| F04 | Calendrier, blocages, prix simples, transitions, idempotence et concurrence | F02, F03, pricing minimal, contraintes DB | T047–T060 |
| F05 | Checkout test, preuve signée, événements durables, remboursements | F04, worker/outbox minimal | T061–T072 |
| F06 | Ménage sans doublon, tâches, maintenance, notifications asynchrones | Événements de réservation, RBAC, stockage | T073–T082 |
| F07 | Règles tarifaires avancées et simulation déterministe V2 | Pricing MVP stable | T105–T109 |
| F08 | Dashboard, métriques définies, filtres et CSV | F04–F06, définitions des revenus | T083–T091 |
| F09 | Contrat de canaux, simulateur, iCalendar et ingestion fiable V2 | F04 et traitement idempotent | T110–T115 |
| F10 | Assistant en lecture seule, autorisations, évaluation V3 | MVP stable, décision données/fournisseur | T116–T120 |

## Exigences non fonctionnelles

- Isolation : autorisation à chaque requête et job ; aucune donnée inter-tenant dans SQL, objets, caches, exports, agrégats ou logs. Tests négatifs au niveau API et PostgreSQL.
- Intégrité : protection SQL des séjours concurrents, transaction par cas d'usage, clés étrangères composites, idempotence persistante, opérations externes récupérables.
- Sécurité : identités à source unique, RBAC serveur, sessions protégées, CSRF si cookies, CORS restreint, secrets hors Git, limitation de débit, logs sans données sensibles.
- Maintenabilité : monolithe modulaire, dépendances explicites, DI à la frontière, migrations, contrats OpenAPI, configuration validée par environnement, erreurs centralisées et interfaces accessibles.
- Reproductibilité : local complet par Docker Compose, seed fictif, tests isolés, lockfiles et versions choisies après vérification de compatibilité. Les fournisseurs réels ne sont requis que pour les recettes d'intégration correspondantes.
- Exploitabilité : journaux structurés, identifiants de corrélation, sondes, métriques, suivi d'erreurs, reprises et restauration prouvées. AWS reste optionnel.

Les volumes, budget, SLO, RPO/RTO, langues, région de données et règles de conservation ne sont pas fixés par la spécification. [Les objectifs provisoires](quality-delivery.md) sont des propositions mesurables, pas des garanties contractuelles.

## Critères de recette du cahier des charges

| Critère original | Preuve à obtenir | Tâches responsables |
| --- | --- | --- |
| A01 : séparation A/B | Matrice de lecture/écriture, références étrangères et pool de connexions | T027, T028, T034 |
| A02 : confirmations concurrentes | Vraies transactions PostgreSQL et barrières ; une confirmation au maximum | T049, T050, T052, T059 |
| A03 : Checkout/webhook | Stripe test réel, signature invalide refusée, répétition sans nouvel effet | T061–T066, T072 |
| A04 : ménage unique | Événement de départ répété/concurrent ; une seule tâche | T074, T082 |
| A05 : calendrier | Départ exclusif, maintenance, options, fuseaux et dates adjacentes | T047–T050, T058–T060 |
| A06 : reporting isolé | Agrégats et CSV A/B, filtres et absence de fuite indirecte | T083–T090 |
| A07 : démarrage local | Clone neuf, `docker compose up --build`, migrations puis seed reproductible | T005–T008, T091 |
| A08 : CI et trois E2E | Logs de CI : qualité, builds, backend/frontend, auth/réservation/opérations | T009, T018, T034, T060, T082, T098 |
| A09 : documentation réelle | README avec commandes exécutées, architecture, limites, captures et OpenAPI | T001, T015, T103 |

## Règles bloquantes avant de coder

La définition du tenant, le protocole de concurrence, l'autorité d'authentification et la politique paiement/confirmation doivent être validés avant leurs phases respectives. Les ambiguïtés sont enregistrées sous D01–D12 dans [les décisions](risks-decisions.md). L'absence d'un choix commercial ne doit pas être remplacée par une règle implicite dans le code.

Le résultat de cette session est un plan révisable. Une tâche documentée n'est ni une fonctionnalité réalisée, ni une Issue publiée, ni une preuve de test.
