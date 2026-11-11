# Règles de développement

## État et autorisations

Le cadrage, le backlog et l'architecture ont été validés le 2026-11-10 (« je valide »). P01 est vérifiée et la PR #10 a été fusionnée sur accord explicite (« continue fusionne »), avec CI verte sur `6af120f`. P02 est fusionnée par la PR #21 sur `04726fe` le 2026-11-11, après CI verte sur `403fb81`. En réponse à la proposition fusion P02 puis démarrage P03, « fait le meilleur choix » délègue ce choix : fusion réalisée et P03 autorisée. Consulter les suivis [P01](docs/progress/phase-01.md), [P02](docs/progress/phase-02.md) et [P03](docs/progress/phase-03.md). Attendre l'accord avant P04 ou une phase suivante.

L'utilisateur a autorisé la publication GitHub le 2026-11-10 (« oui ») : dépôt privé `ABDOUUisHERE/ai-property-management-saas`, push de `main` et `feat/t001-local-foundations`, neuf jalons, Issues P01 et PR de revue du lot validé. Poursuivre les mises à jour nécessaires à ce lot sans redemander cette autorisation. Les liens réels figurent dans [le suivi P01](docs/progress/phase-01.md).

La publication GitHub et sa poursuite sont autorisées (« oui », « push ca », puis « continue […] le max de contributions »). L'accord délégué du 2026-11-11 couvre le démarrage et la publication des incréments P03 : Issues du backlog, branche, commits vérifiés et PR de revue. La fusion d'un lot P03 et toute dépense AWS demandent un accord couvrant l'action. Conserver les accords déjà obtenus. La protection de `main` avait été refusée lorsque le dépôt était privé ; sa visibilité a depuis été observée publique. Préserver la configuration distante actuelle.

## Avant un changement

1. Lire le [cahier des charges](property_management_saas_cahier_des_charges.md), puis la tâche et ses dépendances dans [le backlog](docs/backlog/README.md). Identifier les critères d'acceptation à prouver.
2. Pour un changement d'architecture ou de frontière entre modules, lire [le système](docs/architecture/system-design.md) et les [ADRs](docs/adr/README.md). Pour les règles de réservation, d'argent, d'accès ou de reporting, lire [le modèle métier](docs/architecture/domain-data.md). Utiliser les termes du [glossaire](GLOSSARY.md).
3. Proposer l'Issue et un plan minimal avant l'implémentation ; tant que la publication n'est pas autorisée, utiliser l'identifiant local de tâche. Vérifier les consignes applicables et l'état réel du dépôt avant de modifier des fichiers.

## Implémentation après validation

- Garder les règles métier dans les services/cas d'usage, les routes dans l'adaptation HTTP et les accès SQL dans les repositories. Ajouter seulement les couches nécessaires au module.
- Résoudre l'identité, vérifier l'appartenance actuelle et construire un contexte tenant côté serveur. Toute donnée métier et toute exécution différée doivent être contextualisées. Utiliser les contraintes composites prévues pour empêcher les références entre entreprises.
- Pour disponibilité et réservations, suivre le protocole transactionnel documenté ; PostgreSQL reste l'autorité de concurrence. Les appels réseau s'effectuent hors des transactions de réservation.
- Les paiements restent en mode test. Un retour navigateur ne prouve jamais le paiement ; signature, déduplication et rapprochement sont obligatoires.
- Préserver l'historique, minimiser les données personnelles, masquer les secrets dans les logs et utiliser exclusivement des données de démonstration fictives.
- Toute évolution du schéma inclut une migration Alembic et une stratégie de restauration ; vérifier la migration sur PostgreSQL réel.

## Validation et livraison

- Avant de déclarer une tâche terminée, exécuter ses contrôles pertinents et les contrôles obligatoires disponibles dans le dépôt. Rapporter les commandes réellement exécutées, résultats et limites ; un test non exécuté reste non vérifié.
- Pour tout accès tenant, ajouter les cas d'autorisation et de refus cross-tenant ; pour une mutation de disponibilités, vérifier concurrence et frontières de dates ; pour un webhook, vérifier signature, répétition et ordre inversé. Consulter [le plan qualité](docs/architecture/quality-delivery.md).
- Livrer par branche `feat/`, `fix/`, `test/`, `refactor/` ou `docs/`, commits Conventional Commits atomiques et PR cohérente lorsque ces actions sont autorisées. Appliquer [le workflow GitHub](docs/github-workflow.md).
- Les 50 à 100 contributions souhaitées sont un objectif indicatif subordonné au travail réel. Aucun commit vide, découpage artificiel ou manipulation de dates.
- En fin de séance : fichiers modifiés, preuves, problèmes restants, prochain lot et activité GitHub réelle. Attendre l'accord avant la phase suivante ; corriger les critères échoués avant d'avancer.
