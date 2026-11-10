# E06 — Paiements de test

Phase de chaque tâche : **P06**. Version : **MVP**. Gate : P05 vérifiée et accord ; D04 validée ; credentials Stripe test seulement quand nécessaires à l'intégration réelle.

## FEA18 — Checkout récupérable

### US18 — Comme manager, je veux faire payer une réservation autorisée sans créer deux tentatives actives.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T061 — Modèle et adapter Stripe | Migrer tentatives/paiements, clés stables et port fournisseur | payments | P0 | T060, T019 | IDs compte/mode uniques, test seulement, aucune carte, secrets hors DB métier | Migrations/RLS, mode live refusé, adapter timeout/erreur | 5 |
| T062 — Création Checkout | Orchestrer option ou séjour confirmé impayé, appel externe et correspondance persistée | payments/reservations | P0 | T061, T053 | Prix serveur, tentative active unique, expiration alignée ; durée résiduelle insuffisante refusée ; pas de réseau sous lock | Retry/double clic, crash après Stripe, devises/unités, option trop courte et confirmé impayé | 8 |

## FEA19 — Preuves financières et rapprochement

### US19 — Comme owner, je veux que seuls des paiements vérifiés affectent mes séjours et leur historique.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T063 — Entrée webhook signée | Vérifier corps brut/signature et persister inbox avant 2xx | payments/security | P0 | T061, T013 | Déduplication event ID, données expurgées, inbox non résolue inaccessible, DB en panne réessayable | Signature invalide, payload altéré, timestamp, doublon simultané, panne DB | 5 |
| T064 — Traitement idempotent | Consommer inbox avec verrou et invariants métier | payments/workers | P0 | T063, T019 | Répétition sans nouvel effet, événement connu mais non traité récupérable | Crash avant/après effet, redelivery, même objet avec events distincts | 5 |
| T065 — Ordre et rapprochement | Comparer compte/mode/session/montant/devise et état fournisseur | payments | P0 | T064, T062 | Événements hors ordre sans régression ; correspondance locale autoritaire | Succès/échec inversés, mauvais montant/devise, tenant metadata falsifié | 5 |
| T066 — Paiement et confirmation | Appliquer paid et commande réservation dans transaction cohérente | payments/reservations | P0 | T065, T056 | Redirect sans effet financier, une confirmation, option toujours validée | Redirect seul, webhook payé doublé, conflit inventaire et annulation | 5 |
| T067 — Remboursement intégral | Ajouter commande autorisée, tentative et preuve fournisseur | payments | P0 | T066, T030, T029 | Owner seulement, cumul borné à encaissé, demande séparée du résultat, audit | Répétition/timeout, montant excessif, rôle manager/staff refusé, events inversés | 5 |
| T068 — Expiration et anomalies | Rapprocher session avant libération et gérer succès tardif | payments/workers | P0 | T066, T053, T067 | Unité non réattribuée à tort, paiement réel conservé, anomalie consultable | Expiration/webhook simultanés, session ambiguë, unité déjà revendue | 8 |

## FEA20 — Visibilité et recette Stripe

### US20 — Comme gestionnaire, je veux suivre paiement, anomalie et remboursement avec une preuve vérifiable.

| ID — titre | Description | Module | Priorité | Dépendances | Critères d'acceptation | Tests nécessaires | Complexité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T069 — Résilience traitement paiement | Éprouver outbox/inbox/worker et reprise après perte broker | payments/quality | P0 | T068, T019 | Aucune perte d'intention ; reprise bornée, échec final visible | Redis vidé, worker tué aux fenêtres critiques, replay et doublons | 5 |
| T070 — Historique et anomalies API | Exposer états autorisés et opérations de résolution auditée | payments | P1 | T068 | Tenant/permissions, correspondance sans données sensibles, aucune modification libre de paid | API A/B, accès rôle, résolution répétée et audit | 3 |
| T071 — Interface paiements | Afficher Checkout test, attente, historique et remboursement | frontend/payments | P1 | T070, T062, T017 | Succès uniquement depuis serveur, retour tardif/pending compréhensible, anomalie visible | RTL redirect non payé, polling borné, rôle et double clic remboursement | 3 |
| T072 — Recette Stripe test | Vérifier parcours fournisseur réel et fixtures CI distinctes | quality/payments | P0 | T069, T071, T060 | Checkout test et webhook signé réellement prouvés ; limites d'accès signalées | Stripe CLI/test : succès/doublon/remboursement ; fixtures invalides/hors ordre en CI | 5 |
