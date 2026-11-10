# Contribuer

Le cadrage et le backlog ont été validés le 2026-11-10. La phase P01 prépare uniquement le dépôt et l'environnement ; les fonctionnalités métier commencent après validation des fondations correspondantes.

## Préparer un changement

Lire [AGENTS.md](AGENTS.md), la tâche dans [le backlog](docs/backlog/README.md) et ses dépendances. Utiliser son identifiant local tant que les Issues ne sont pas publiées. Décrire le problème, le périmètre et les preuves attendues avant d'implémenter.

Créer une branche `feat/`, `fix/`, `test/`, `refactor/` ou `docs/` par lot cohérent. Utiliser des Conventional Commits et conserver des changements atomiques utiles. L'objectif indicatif de contributions ne doit jamais conduire à des commits vides ou à un fractionnement artificiel.

## Environnement et validation

Suivre [le démarrage local](docs/runbooks/local-development.md). Les dépendances Python d'outillage sont verrouillées par `uv.lock`. Les contrôles de la phase courante sont documentés dans ce runbook ; rapporter les commandes réellement exécutées et leurs résultats. Les tests backend/frontend seront ajoutés avec leurs composants, sans déclarer de suite fictive.

Les secrets sont générés localement dans des fichiers ignorés. Ne pas joindre `.env`, clés privées, tokens, données personnelles ou sorties Docker contenant des secrets à une Issue/PR. Utiliser uniquement des données fictives. Vérifier le diff et les fichiers suivis avant de committer.

## Revue et livraison

Une PR explique le comportement livré, ses critères d'acceptation, les preuves, les migrations et les limites. Lier les tâches concernées ; ajouter des captures pour une interface réellement disponible. Tous les contrôles applicables doivent être verts avant fusion.

Créer un dépôt distant, pousser, publier une Issue/PR, fusionner ou déployer exige une autorisation couvrant l'action. L'acceptation du cadrage n'est pas une autorisation générale de publication. Conserver les autorisations déjà accordées dans leur périmètre.

La licence du projet n'a pas encore été choisie ; ce document n'accorde aucune licence de redistribution. Les composants tiers conservent leurs licences respectives.
