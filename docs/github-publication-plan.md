# Publication GitHub préparée — autorisation en attente

Le cadrage et les 120 tâches sont validés. La publication reste une action distincte. Ce plan prépare un résultat concret à approuver ; il ne décrit pas des ressources déjà créées.

## Destination et contenu proposés

- Propriétaire : compte connecté **ABDOUUisHERE**.
- Nom : **ai-property-management-saas**.
- Visibilité proposée : **privée**.
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

Ce plan n'autorise pas son exécution. Enregistrer chaque URL créée dans le suivi de phase après vérification et rapporter séparément commits locaux, pushes, Issues, PR et contributions visibles.
