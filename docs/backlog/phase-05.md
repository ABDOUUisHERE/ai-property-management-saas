# E05 — Disponibilités et réservations

Phase de chaque tâche : **P05**. Version : **MVP**. Gate : P04 vérifiée et accord ; D03/D04/D08 validées. Le worker d'expiration est livré ici, pas en phase 7.

## FEA14 — Calendrier et intégrité d'inventaire

### US14 — Comme manager, je veux connaître les nuitées disponibles et bloquer les unités en maintenance.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T047 — Dates et lecture calendrier | Définir plages civiles et contrat InventoryReadPort | availability | P0 | T046, T015 | Départ exclusif, plages bornées, timezone affichée et filtres tenant | Adjacence, année bissextile, DST, plage vide et unité étrangère | 3 |
| T048 — Blocages maintenance | Migrer et exposer blocages manuels annulables | availability | P0 | T047, T037 | Dates/unité validées, permissions, historique et audit des blocages | CRUD tenant, chevauchements, blocage annulé et dates adjacentes | 3 |
| T049 — Exclusion SQL des séjours | Migrer réservations et exclusion GiST, brancher garde historique des unités | reservations/database | P0 | T047, T043 | `btree_gist`, états bloquants, FK composites, CHECK dates/montant ; suppression/archivage protégés avec vrais séjours | PostgreSQL réel : chevauchement/adjacence, UPDATE statut/dates, FK historique et archivage | 5 |
| T050 — Verrou d'inventaire partagé | Appliquer verrou unité et relecture à tous les writers | availability/reservations | P0 | T048, T049 | Réservation/maintenance sérialisées, ordre des locks, aucun appel réseau en transaction | Course réservation/blocage, déplacement 2 unités, rollback et timeout | 8 |

## FEA15 — Création fiable et options

### US15 — Comme manager, je veux créer une réservation une seule fois malgré doubles clics et concurrence.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T051 — Commandes de réservation | Créer draft/pending et lectures avec validation capacité/relations | reservations | P0 | T050, T055 | Unité/voyageur tenant, montant serveur, version et transitions dédiées | API états, surcapacité, ressource archivée/étrangère, payload sensible | 5 |
| T052 — Idempotence de création | Persister clé, hash et résultat dans transaction | reservations | P0 | T051 | Même clé/payload même réservation ; payload différent 409 ; scope acteur/tenant | Requêtes simultanées, réponse perdue, rollback, clé réutilisée/durée | 5 |
| T053 — Options et expiration | Programmer fin d'option et hook de rapprochement fournisseur | reservations/workers | P0 | T052, T019 | Expiration persistée sous lock, option bloquante jusque-là, présence paiement ambigu traitée par port | Horloge contrôlée, worker arrêté/repris, annulation/confirmation concurrente | 5 |

## FEA16 — Prix MVP et cycle de séjour

### US16 — Comme gestionnaire, je veux un prix détaillé stable et des transitions de séjour contrôlées.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T054 — Calcul simple du prix | Persister/configurer tarif de base, frais/taxes simples et remise ; exposer calcul | pricing | P0 | T047, T037 | Configuration API autorisée, entiers/décimal, exposant devise et règle d'arrondi approuvée ; pas de saison avancée | Configuration A/B/rôles, frontières nuits, remises plafonnées, devises 0/2/3 décimales et zéro | 5 |
| T055 — Devis et snapshot | Exposer simulation et figer lignes/allocation par nuit | pricing/reservations | P0 | T054, T049 | Total reproductible, versions et devise figées, changement de tarif sans effet historique | Quote/création identiques, arrondis de répartition, client falsifiant total | 3 |
| T056 — Confirmer/annuler/arriver/partir | Implémenter machine d'état et événements métier uniques | reservations | P0 | T053, T029 | Transitions autorisées, confirmation manuelle auditée, départ émis une fois ; PATCH protégé | Toutes transitions valides/interdites, répétition, version perdue et dates | 5 |

## FEA17 — Parcours de réservation et recette

### US17 — Comme utilisateur, je veux voir le calendrier et comprendre immédiatement un conflit de disponibilité.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T057 — Formulaire et détail séjour | Créer choix unité/voyageur/dates, devis/commandes et paramètres de prix simples | frontend/reservations | P1 | T056, T045 | Clé stable au retry, prix serveur, configuration tarifs selon rôle, erreurs 409 et états accessibles | RTL double clic, tarifs, devis expiré, validation dates et refus rôle | 5 |
| T058 — Calendrier UI | Afficher séjours/options/maintenance et filtres organisation | frontend/availability | P1 | T056, T040 | Checkout exclusif visible, fuseau/état distingués sans seule couleur | RTL navigation clavier, filtres, adjacence et données tenant | 5 |
| T059 — Recette concurrence réelle | Exécuter matrice de courses PostgreSQL avec barrières | quality/reservations | P0 | T050, T052, T053, T056 | Au plus une confirmation concurrente ; aucun conflit maintenance/archivage ; état final contrôlé | Multi-connexions, lock ordre/timeout, déplacement et archivage pendant création | 8 |
| T060 — E2E réservation en CI | Vérifier création/devis/calendrier/états sur stack réelle | quality/frontend | P0 | T057, T058, T059, T018 | Parcours E2E réservation vert, deux sessions concurrentes et A/B | Playwright création/conflit/annulation, expiration et départ exclusif | 5 |
