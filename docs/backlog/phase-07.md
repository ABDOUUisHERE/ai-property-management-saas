# E07 — Opérations et notifications

Phase de chaque tâche : **P07**. Version : **MVP**. Gate : P06 vérifiée et accord ; règle métier D10 validée.

## FEA21 — Tâches et ménage automatique

### US21 — Comme manager, je veux qu'un séjour crée exactement une tâche de ménage selon ma règle.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T073 — Modèle tâches et configuration | Migrer tâches, affectations et règle confirmation/départ | operations | P1 | T072, T026 | Statuts/priorités/échéances, membre du tenant, règle par organisation et valeur par défaut | Migrations/RLS/FK, mauvais membre, règle inconnue et échéance locale | 3 |
| T074 — Génération ménage unique | Consommer événements séjour et dédupliquer par clé métier | operations | P0 | T073, T056, T019 | Une tâche séjour/type, événements répétés sans doublon, annulation adaptée | Confirmation/départ répétés et concurrents, replay après crash, tâche commencée/terminée | 5 |
| T075 — Gestion manuelle des tâches | Exposer CRUD non destructeur, attribution et transitions | operations | P1 | T073, T030, T029 | Staff limité à ses tâches, réaffectation membre retiré, historique conservé | API rôles/A/B, transition invalide, note et affectation étrangère | 3 |

## FEA22 — Maintenance et communication fiable

### US22 — Comme agent opérationnel, je veux signaler un problème et recevoir mes tâches malgré une panne temporaire.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T076 — Files d'échecs et reprise | Persister échecs, retries bornés et commande de replay | workers/operations | P0 | T074, T069 | Erreur expurgée, tentative/échéance, replay autorisé/audité et idempotent | Backoff/épuisement, erreur permanente, replay concurrent et tenant | 5 |
| T077 — Tickets maintenance | Ajouter signalement, assignation et historique d'interventions | operations | P1 | T075, T048 | Workflow contrôlé, ticket distinct du blocage explicite, droit staff | API transitions, A/B, signalement staff et conflit de blocage | 3 |
| T078 — Photos maintenance | Associer fichiers privés aux tickets | operations/storage | P1 | T077, T038 | Même limites/autorisation que photos, accès staff borné | Upload étranger, URL expirée, retrait/orphelin et taille/type | 2 |
| T079 — Messages email locaux | Étendre le port email des invitations aux templates opérationnels | notifications | P1 | T073, T025, T019, T006 | Adapter Mailpit réutilisé, contenu minimisé sans secret et destinataire autorisé | Template/échappement, réception locale, langue/fuseau et donnée masquée | 3 |
| T080 — Livraison email asynchrone | Relier événements, tentatives, déduplication et échecs | notifications | P0 | T079, T076 | Reprise sûre, unicité métier, retries bornés ; limites de doublon fournisseur explicites | SMTP indisponible, timeout ambigu, replay, doublon et dead-letter | 5 |

## FEA23 — Interface et recette opérations

### US23 — Comme staff, je veux exécuter mes interventions depuis une interface qui respecte mon périmètre.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T081 — Interface opérations | Créer listes, affectations, tickets, photos et consultation des échecs selon rôle | frontend/operations | P1 | T075, T078, T080, T032 | États accessibles, filtres tenant/assignation et aucune PII hors besoin | RTL tâches staff, upload, erreurs, changement tenant et clavier | 5 |
| T082 — E2E ménage et maintenance | Vérifier départ → tâche unique → exécution → notification | quality/operations | P0 | T081, T074, T080, T060 | Troisième E2E critique intégré CI, audit et refus A/B verts | Playwright staff/manager, événement répété, crash et SMTP en panne | 5 |
