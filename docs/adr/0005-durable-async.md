---
status: accepted
date: 2026-11-10
accepted: 2026-11-10
decision: D10
---

# Outbox PostgreSQL et consommateurs idempotents

Proposition : écrire l'événement outbox dans la transaction métier, le dispatcher vers Celery/Redis puis dédupliquer les effets dans PostgreSQL. La même base conserve l'intention, les reçus de consommation et les échecs définitifs. Redis sert de transport, pas de seule copie d'un travail engagé.

Un envoi direct après commit peut se perdre entre commit et publication ; un envoi avant commit peut annoncer une transaction annulée. Un broker seul avec retry ne ferme pas cette fenêtre. Une queue PostgreSQL seule serait une alternative plus compacte ; Celery/Redis est proposé pour les mécanismes de worker et parce que Redis fait déjà partie de la stack, au prix d'une exploitation supplémentaire.

La garantie est livraison au moins une fois et effet métier idempotent, pas « exactly once ». Clés uniques pour ménage, paiements et notifications ; lease/timeout de dispatch, redelivery et replay audité. Les primitives arrivent avant les paiements, même si les consommateurs métier opérations arrivent plus tard. Un test de perte Redis et de crash après effet est obligatoire.
