# Contribuer

Le cadrage et le backlog ont été validés le 2026-11-10. P01 est fusionnée ; P02 livre l'architecture exécutable. Les fonctionnalités métier commencent après validation des fondations correspondantes.

## Préparer un changement

Lire [AGENTS.md](AGENTS.md), la tâche dans [le backlog](docs/backlog/README.md) et ses dépendances. Utiliser son identifiant local tant que les Issues ne sont pas publiées. Décrire le problème, le périmètre et les preuves attendues avant d'implémenter.

Créer une branche `feat/`, `fix/`, `test/`, `refactor/` ou `docs/` par lot cohérent. Utiliser des Conventional Commits et conserver des changements atomiques utiles. L'objectif indicatif de contributions ne doit jamais conduire à des commits vides ou à un fractionnement artificiel.

## Environnement et validation

Suivre [le démarrage local](docs/runbooks/local-development.md), puis [le runbook applicatif](docs/runbooks/application-development.md). `uv.lock` verrouille l'outillage, `backend/uv.lock` le backend et `frontend/package-lock.json` le frontend. Exécuter les contrôles correspondant aux fichiers modifiés et rapporter leurs résultats réels. Un changement d'interface passe aussi les tests navigateur et les audits d'accessibilité des écrans concernés.

Les secrets sont générés localement dans des fichiers ignorés. Ne pas joindre `.env`, clés privées, tokens, données personnelles ou sorties Docker contenant des secrets à une Issue/PR. Utiliser uniquement des données fictives. Vérifier le diff et les fichiers suivis avant de committer.

## Revue et livraison

Une PR explique le comportement livré, ses critères d'acceptation, les preuves, les migrations et les limites. Lier les tâches concernées ; ajouter des captures pour une interface réellement disponible. Tous les contrôles applicables doivent être verts avant fusion.

Créer un dépôt distant, pousser, publier une Issue/PR, fusionner ou déployer exige une autorisation couvrant l'action. L'acceptation du cadrage n'est pas une autorisation générale de publication. Conserver les autorisations déjà accordées dans leur périmètre.

La licence du projet n'a pas encore été choisie ; ce document n'accorde aucune licence de redistribution. Les composants tiers conservent leurs licences respectives.
