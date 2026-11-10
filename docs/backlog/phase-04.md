# E04 — Biens et voyageurs

Phase de chaque tâche : **P04**. Version : **MVP**. Gate : P03 vérifiée et accord ; préciser D07 pour les données personnelles, D08 pour devise/fuseau.

## FEA11 — Modèle et gestion des biens

### US11 — Comme manager, je veux décrire et maintenir mes ressources louables sans détruire leur historique.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T035 — Schéma des biens/unités | Migrer propriétés, unités et périodes d'activité | properties | P0 | T034, T011 | FK tenant, timezone/devise/capacité contrôlées, historique conservable | Migrations, CHECK/FK/RLS runtime, valeurs IANA et devise invalides | 3 |
| T036 — CRUD propriétés | Exposer création, lecture et édition validées | properties | P1 | T035, T030 | Tri/pagination tenant, équipements, permissions, changement devise/fuseau protégé | API CRUD A/B, pagination, patch interdit et validation | 3 |
| T037 — Unités et archivage | Exposer unités, capacité et contrat de protection de l'historique | properties | P0 | T036 | RESTRICT/archivage prévus, périodes conservées ; port de garde historique/futur testé, intégration séjours complétée en T049/T059 | Garde simulée avec/sans historique, dates actives, unité étrangère ; preuve réelle en P05 | 5 |
| T038 — Stockage objet privé | Créer adapter upload/download autorisé et métadonnées | properties/storage | P0 | T035, T006 | Clé interne tenant, URLs signées courtes, tailles/types bornés, objets privés | Objet A/B, URL expirée, MIME/taille, nom malveillant, upload orphelin | 5 |

## FEA12 — Interface portefeuille

### US12 — Comme gestionnaire, je veux retrouver mes propriétés et leurs unités depuis une interface accessible.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T039 — Liste et détail propriétés | Créer filtres simples, formulaires et états UI | frontend/properties | P1 | T036, T032 | Pagination stable, validation et erreurs, devise/fuseau visibles | RTL formulaire/empty/error, clavier et requêtes tenant | 3 |
| T040 — Écrans unités et archivage | Créer/éditer unités et confirmer archivage | frontend/properties | P1 | T037, T039 | Historique et refus serveur compréhensibles, actions selon rôle | RTL validation capacité, conflit archivage, accès staff limité | 3 |
| T041 — Photos des propriétés | Relier API et UI de photos au stockage privé | properties/frontend | P1 | T038, T039 | Upload sécurisé, ordre/description, retrait contrôlé et erreurs réseau | Upload/retrait A/B, preview accessible, fichier rejeté | 3 |
| T042 — Recette portefeuille | Vérifier biens, unités et photos avec données A/B | quality/properties | P0 | T040, T041 | CRUD/archivage/RLS et objets isolés prouvés ; seeds fictifs | API PostgreSQL, UI et tentative de lecture objet étranger | 3 |

## FEA13 — Fiches voyageurs

### US13 — Comme manager, je veux gérer mes voyageurs en limitant les données personnelles exposées.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T043 — Fiches voyageurs API | Migrer et exposer fiches locales au tenant et historique autorisé | guests | P1 | T034, T011 | Téléphone facultatif, email non unique global, champs minimisés | API A/B, doublons d'email inter-tenant, validation et FK | 3 |
| T044 — Masquage et anonymisation | Appliquer vues par rôle et conservation approuvée | guests/security | P0 | T043, T030, T029 | Staff ne reçoit pas les champs interdits, anonymisation préserve faits historiques | Réponses staff, anonymisation répétée, refus rôle, audit sans PII | 5 |
| T045 — Interface voyageurs | Créer liste/recherche/formulaire et historique accessible | frontend/guests | P1 | T044, T032 | Chargement/erreur/empty, masquage et confirmations cohérents | RTL champs masqués, recherche et anonymisation autorisée | 3 |
| T046 — Recette voyageurs | Vérifier associations, privacy et seeds fictifs | quality/guests | P0 | T045, T042 | Aucune référence étrangère, aucune donnée personnelle réelle dans seed | Tests PostgreSQL/API/UI A/B et conservation avec historique | 3 |
