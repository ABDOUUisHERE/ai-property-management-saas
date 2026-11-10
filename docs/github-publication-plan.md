# Publication GitHub — effectuée, PR en revue

Le cadrage et les 120 tâches sont validés. L'utilisateur a autorisé la publication le 2026-11-10 (« oui »). Le dépôt privé, les deux branches, neuf jalons, neuf Issues P01 et la PR de revue ont été publiés et vérifiés. La fusion et P02 restent des étapes distinctes.

Liens : [dépôt](https://github.com/ABDOUUisHERE/ai-property-management-saas), [jalons](https://github.com/ABDOUUisHERE/ai-property-management-saas/milestones), [Issues P01](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues), [PR #10](https://github.com/ABDOUUisHERE/ai-property-management-saas/pull/10), [CI réussie sur a4f4f01](https://github.com/ABDOUUisHERE/ai-property-management-saas/actions/runs/42837783466).

## Destination et contenu proposés

- Propriétaire : compte connecté **ABDOUUisHERE**.
- Nom : **ai-property-management-saas**.
- Visibilité vérifiée : **privée**.
- Description : « Multi-tenant short-term rental management SaaS — FastAPI, React and PostgreSQL. »
- Licence : non choisie ; aucun fichier LICENSE ajouté implicitement.
- Historique : envoyer les commits locaux réels, sans modifier dates/auteurs.
- Jalons : P01 à P09 selon [la roadmap](roadmap.md), sans dates artificielles.
- Premier lot d'Issues : **T001 à T009**, avec description, hiérarchie, module, priorité, dépendances, critères/tests/complexité de [P01](backlog/phase-01.md). Les tâches suivantes seront publiées par phase.
- PR de revue pour les fondations locales, liée aux tâches correspondantes, avec preuves locales et vérification réelle des GitHub Actions après publication.

Le dépôt reste autonome : aucune dépendance applicative aux autres projets de l'utilisateur. Les dossiers `.env`, `.local`, `.cache` et `.venv` ne sont pas envoyés.

## Procédure après autorisation

1. Vérifier à nouveau l'absence d'un dépôt homonyme accessible et la destination du compte.
2. Créer le dépôt privé et configurer `origin`, puis lire l'URL et la visibilité réellement retournées.
3. Envoyer le commit initial de documentation sur `main` et la branche des fondations ; publier les neuf milestones et les Issues avec leurs IDs locaux, puis relier les dépendances à leurs URLs réelles. Garder les dates réelles de publication.
4. Ouvrir la PR avec les critères de phase et les commandes réellement exécutées ; vérifier la CI distante. Les Issues ne sont clôturées qu'avec la livraison effectivement revue/fusionnée selon l'autorisation disponible.
5. Configurer les contrôles requis si l'offre et les droits le permettent. Le token actuel ne prouve pas un droit d'écriture Project ; le board reste optionnel et n'exige pas d'élargir les accès pour livrer.

## Limites constatées

La protection de branche `main` (PR, checks `quality`/`infrastructure`, interdiction force-push/suppression) a été demandée via l'API et refusée avec HTTP 403 : l'offre GitHub actuelle ne permet pas cette configuration sur ce dépôt privé. Aucun changement de visibilité ni achat n'a été effectué. Les règles de PR/revue restent une convention tant que cette protection n'est pas disponible.

Le token fournit `read:project`, sans droit d'écriture Project. Le board optionnel n'a pas été créé et aucun élargissement de scopes n'a été demandé. Les milestones et labels restent utilisables. La licence n'est pas choisie ; aucun fichier LICENSE n'a été ajouté.

Les URLs et résultats réels sont enregistrés dans [le suivi P01](progress/phase-01.md). Les Issues et la PR restent ouvertes ; aucun résultat de fusion ni contribution visible sur le profil n'est déduit des seuls pushes.
