# Extensions après MVP

Gate commun : T104 livré, nouveau périmètre validé et accord de phase. Aucun de ces éléments n'est nécessaire au MVP. Le MVP n'attend ni tarifs avancés, ni canaux, ni IA.

## E10 — Tarification avancée

Phase de chaque tâche de E10 : **PX2**. Version : **V2**.

### FEA31 — Règles et simulation

#### US31 — Comme manager, je veux simuler des tarifs saisonniers dont je comprends la priorité.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T105 — Modèle de règles avancées | Versionner saisons, jours/semaine, minimum séjour et remises | pricing | P2 | T104 | Priorités/chevauchements explicités, scope unité/tenant et historique figé | Migrations/RLS, règles incompatibles, frontières saison | 3 |
| T106 — Calcul déterministe avancé | Étendre moteur en conservant contrats MVP et arrondis | pricing | P2 | T105, T054 | Même entrée/version même sortie, priorité expliquée et minimum appliqué | Jeux de frontières, jours fériés si retenus, interaction remise/taxes et DST | 5 |
| T107 — Simulation détaillée | Exposer devis avancé et explication ligne par ligne | pricing/api | P2 | T106 | Aucune mutation de séjour, version/priorité visibles et données tenant | Comparaison simulation/création, tarif modifié pendant réservation et A/B | 3 |

### FEA32 — Gestion et recette des tarifs

#### US32 — Comme gestionnaire, je veux éditer les règles sans modifier mes réservations historiques.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T108 — Éditeur de règles | Créer UI de plages/priorités/simulation accessible | frontend/pricing | P2 | T107 | Conflits compréhensibles, prévisualisation et publication contrôlée | RTL règles adjacentes/concurrentes, validation et rôle staff refusé | 5 |
| T109 — Recette tarifs V2 | Vérifier non-régression MVP et historique/reporting | quality/pricing | P2 | T108 | Réservations passées inchangées, calcul avancé reproductible sans promesse ML | Tests prix/frontières, E2E simulation/réservation et agrégats | 5 |

## E11 — Canaux et simulation

Phase de chaque tâche de E11 : **PX2**. Version : **V2**. Peut progresser indépendamment de E10 après MVP.

### FEA33 — Adaptation et échange de calendriers

#### US33 — Comme gestionnaire, je veux expérimenter une synchronisation sans prétendre posséder un accès partenaire.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T110 — Contrat ChannelAdapter | Définir événements externes, identifiants et mapping tenant/unité | channels | P2 | T104 | Interface indépendante fournisseur, versions et contrat de déduplication | Tests de contrat adapter fictif, mapping ambigu ou étranger | 3 |
| T111 — Simulateur local | Générer créations/modifications/annulations externes signées pour démo | channels | P2 | T110 | Aucun accès officiel revendiqué, répétition/ordre inversé pilotables | Scénarios simulés, signature, payload invalide et ressource inconnue | 3 |
| T112 — Import/export iCalendar | Ajouter échange borné avec UID stables et limites de synchro | channels | P2 | T110 | Polling non instantané visible ; URL source validée, protection SSRF et accès export | Fuseaux/UID/annulation, URL réseau privé refusée, parsing et export A/B | 5 |

### FEA34 — Ingestion et conflits

#### US34 — Comme manager, je veux voir les conflits importés sans surbooking silencieux.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T113 — Ingestion fiable | Persister inbox externe, dédupliquer, ordonner par version fiable et réessayer | channels/workers | P2 | T111, T112, T064 | Signatures lorsque disponibles, commande réservation sous même lock, échecs visibles | Répétition, hors ordre, retry, conflit unité et mapping tenant | 8 |
| T114 — Interface anomalies canaux | Exposer statut sync, conflit et résolution autorisée | frontend/channels | P2 | T113 | Aucun écrasement automatique d'un séjour confirmé, décision auditée | RTL conflit, retry, refus de rôle et incohérence source | 3 |
| T115 — Recette canaux simulés | Vérifier simulateur/iCalendar et documentation des limites | quality/channels | P2 | T114 | Conflit détecté, intégration explicitement simulée, anti-surbooking local conservé | E2E import/replay/annulation, concurrence import/manuelle et SSRF | 5 |

## E12 — Assistant interne facultatif

Phase de chaque tâche de E12 : **PX3**. Version : **V3**. Dépend du MVP, pas de V2. Fournisseur, budget et données autorisées exigent un cadrage préalable.

### FEA35 — Accès en lecture seule

#### US35 — Comme manager, je veux interroger mes données sans donner à l'assistant des droits supplémentaires.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T116 — Cadrage IA et données | Définir fournisseur, budget, données minimisées et protocole d'évaluation | assistant/docs | P3 | T104 | Usage optionnel accepté, rétention/transfert validés, aucun besoin d'action autonome | Revue de périmètre, cas de fuite et dataset fictif d'évaluation | 3 |
| T117 — Outils métier de lecture | Exposer outils serveur limités au contexte tenant et RBAC courant | assistant | P3 | T116 | Pas de SQL arbitraire, aucune mutation, autorisation à chaque appel | Outil interdit, ID étranger, membre retiré en session et limites de volume | 5 |
| T118 — Orchestration et références | Ajouter réponses fondées sur résultats autorisés et références internes | assistant | P3 | T117 | Absence de résultat reconnue, références consultables, pas de secret/PII inutile | Hallucination, injection dans contenu métier, données périmées et budget dépassé | 8 |

### FEA36 — Interface et évaluation de l'assistant

#### US36 — Comme utilisateur, je veux vérifier les réponses et conserver le contrôle des actions sensibles.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T119 — UI assistant interne | Afficher réponse, références et limites, avec liens vers actions humaines existantes | frontend/assistant | P3 | T118 | Interface accessible, aucune exécution sensible par modèle ; actions normales restent confirmées par humain | RTL sources/erreur/chargement, demande d'action refusée et changement tenant | 5 |
| T120 — Recette IA et bilan | Évaluer pertinence, isolation, injections, coût et latence | quality/assistant | P3 | T119 | Seuils approuvés mesurés, limites publiées, désactivation possible sans casser MVP | Dataset évalué, red-team A/B, outils readonly et arrêt fournisseur | 5 |
