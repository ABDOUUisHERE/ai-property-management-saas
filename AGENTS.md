# Règles de développement

## État et autorisations

Le cadrage, le backlog et les recommandations d'architecture ont été validés par l'utilisateur le 2026-11-10 (« je valide »). La phase P01 est autorisée : conventions, Git local, dépendances Docker et CI minimale. Consulter [le suivi P01](docs/progress/phase-01.md) pour les résultats réels et les paramètres encore ouverts. Attendre l'accord de l'utilisateur avant de commencer P02 ou une phase suivante.

Créer un dépôt distant, publier des Issues, pousser, ouvrir une PR ou fusionner exige une autorisation couvrant l'action. Conserver les autorisations déjà accordées et leur périmètre ; ne pas les redemander pour chaque incrément couvert. Le backlog est validé ; sa publication attend une autorisation distante. AWS reste optionnel et non autorisé au déploiement.

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
