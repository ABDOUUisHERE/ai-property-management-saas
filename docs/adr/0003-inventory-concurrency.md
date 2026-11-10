---
status: accepted
date: 2026-11-10
accepted: 2026-11-10
decision: D03
---

# Exclusion des réservations et coordination par verrou d'unité

Le cahier des charges exige une exclusion PostgreSQL sur les réservations. Proposition complémentaire : verrouiller l'unité et relire son inventaire dans chaque mutation de séjour **et** de blocage maintenance. L'exclusion protège les séjours bloquants ; le verrou commun coordonne les deux tables et les changements d'état/date. Les options `pending` bloquent jusqu'à transition persistée d'expiration ou confirmation.

Alternative : un registre unique de toute occupation (séjours, options, maintenance) donnerait une exclusion commune, mais ajouterait une projection à maintenir avec les réservations et leur propre contrainte exigée. Un simple contrôle applicatif sans verrou ou un verrou Redis ne suffit pas. Le protocole proposé est plus limité en structures et convient tant que tous les writers sont sous notre contrôle.

Conséquences : une unité très sollicitée sérialise ses écritures ; ordre de verrou stable lors d'un déplacement ; pas d'appel Stripe sous verrou. Tous les imports et workers suivent le même chemin. L'accès SQL direct non contrôlé pourrait contourner les conflits maintenance : avant d'introduire ce type de writer, renforcer la garantie DB ou adopter le registre commun. La durée des options et la reprise après panne du worker font partie de la recette, dès la phase réservations.
