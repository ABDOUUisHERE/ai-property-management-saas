# Organisation GitHub proposée

Ce document est un plan. Aucun dépôt Git, dépôt distant, milestone, Project, Issue, commit ou PR n'a été créé pendant la session d'analyse. La demande actuelle reporte l'instruction d'initialisation immédiate du cahier des charges.

## Préparation après validation

1. Valider le backlog et D12 : compte propriétaire, nom, visibilité, licence, identité Git et autorisations distantes. Vérifier les accès existants au moment nécessaire, sans demander de credentials prématurément.
2. Initialiser le dépôt local autonome, branche `main`, exclusions de secrets et fichiers générés. Vérifier que nom/email réels correspondent au compte GitHub ; ne pas modifier une identité globale sans justification et accord.
3. Si autorisé, créer le dépôt distant et `origin`, vérifier URL/propriétaire/visibilité. Si accès indisponible, documenter le blocage et poursuivre seulement les actions locales couvertes.
4. Créer les milestones P01–P09 ; V2 et V3 séparés. Publier les éléments approuvés avec ID local, liens de dépendances et champs ci-dessous. Préférer une publication par lots de phase pour garder le board exploitable ; ne pas créer les 120 tâches automatiquement sans validation du contenu.
5. Si Project disponible, utiliser une table et un board avec statut, priorité, phase, module, complexité et relations. Sinon, milestones/labels et documents locaux suffisent ; aucun outil tiers imposé.

## Hiérarchie et champs

Epic = vue d'ensemble avec checklist de features. Feature = capacité livrable regroupant user stories. Story = objectif utilisateur et critères. Technical Task = incrément vérifiable du backlog. Utiliser les relations parent/enfant natives si disponibles, sinon des liens Markdown explicites. Les éléments de regroupement doivent expliquer le besoin et les limites ; ne pas fabriquer des Issues vides pour gonfler l'activité.

Labels proposés : `type:feature`, `type:bug`, `type:test`, `type:docs`, `type:refactor`, `type:infra` ; `priority:P0` à `priority:P3` ; `module:<nom>` ; `status:blocked` pour dépendance externe réelle ; `version:MVP`, `version:V2`, `version:V3`. Le milestone détermine la phase, le Project peut la refléter.

Statuts : Proposed → Ready → In progress → In review → Done. Ready = périmètre et dépendances clairs, décisions nécessaires acceptées. Done = critères prouvés, contrôles verts et livraison revue/fusionnée si le workflow distant est autorisé. Une case cochée localement ne prétend pas qu'une Issue est fermée à distance.

Corps d'Issue à matérialiser plus tard dans un template :

```markdown
[Txxx] Titre concret

Parent : USxx / FEAxx / Exx
Phase : Pxx ; version : MVP/V2/V3
Module : ... ; priorité : ... ; complexité : ...

Objectif / description : ...
Périmètre : ...
Dépendances et décisions : ...

Critères d'acceptation :
- Résultat observable ...

Validation nécessaire :
- Test/cas et preuve attendue ...

Preuves lors de clôture : commandes exécutées, résultats, limites et liens.
```

## Branches, commits et PR

Une branche par lot cohérent depuis `main` à jour : `feat/t051-create-reservation`, `fix/...`, `test/...`, `refactor/...`, `docs/...`. Conventional Commits : `feat(reservations): ...`, `fix(payments): ...`, `test(tenancy): ...`, `docs(architecture): ...`, `refactor(...): ...`, `chore(ci): ...`. Chaque commit apporte un changement réel ; les tests requis sont exécutés avant livraison. Aucun commit vide, retouche sans valeur ni changement artificiel de date.

Une PR peut couvrir plusieurs tâches étroitement liées. Description : problème concret, comportement livré, Issue(s)/ID(s), critères d'acceptation, tests réellement exécutés, migrations et risques de déploiement ; captures seulement si UI réelle. Ne pas présenter une intention comme un résultat. Une PR publiée contient un résultat concret et revu localement, et sa création respecte l'autorisation disponible.

Règles `main` à configurer si l'offre GitHub et les droits le permettent : PR, checks requis et revue humaine si disponible, sinon auto-revue explicite documentée. Rapporter ce qui n'est pas disponible. Fusion seulement avec accord couvrant l'action et CI vérifiée. Proposition : squash pour une PR constituant une seule unité ; conserver plusieurs commits seulement s'ils sont autonomes et utiles à l'historique. Choisir selon lisibilité et réversibilité, jamais pour le graphe.

CI/CD prévue : [plan qualité](architecture/quality-delivery.md). Les templates, workflows et protections seront créés dans les tâches correspondantes. Un document de workflow n'est pas une CI exécutée.

## Contributions authentiques et bilan

L'objectif 50–100 contributions par journée active est indicatif et subordonné au volume de travail utile. Il ne garantit ni ce nombre de commits, ni ce nombre de cases sur le graphe. Mesurer séparément : tâches réalisées, tests ajoutés/exécutés, commits utiles, Issues ouvertes/fermées, PR ouvertes/fusionnées, revues et contributions effectivement affichées.

Les règles GitHub consultées demandent notamment un email lié au compte et des commits sur la branche par défaut ou `gh-pages` pour leur affichage ; Issues/PR suivent leurs propres conditions et limites. Une branche non fusionnée ou un mode de merge différent change ce qui devient visible. Vérifier le graphe au lieu de déduire qu'une action vaut une contribution. [Source : règles du profil GitHub](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference).

Bilan de séance à produire : changements réels, résultats de validation, comptes par type avec URLs vérifiées, statut distant, problèmes ouverts et prochain lot. Si aucune activité GitHub n'a eu lieu, écrire **0**, sans attribuer les documents locaux au graphe. La présente session a uniquement produit des documents locaux.
