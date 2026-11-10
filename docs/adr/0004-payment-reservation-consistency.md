---
status: accepted
date: 2026-11-10
accepted: 2026-11-10
decision: D04
---

# Paiement externe récupérable et réservation protégée par option

Proposition : retenir l'unité avant Checkout, persister la tentative avant l'appel fournisseur et confirmer seulement après preuve signée rapprochée, avec exception explicite de confirmation manuelle auditée. Le paiement et le séjour ont des états distincts. Une transaction locale ne peut pas englober Stripe ; les reprises s'appuient donc sur les clés d'idempotence, l'inbox durable et des commandes métier idempotentes.

Alternative : confirmer d'abord tous les séjours puis encaisser ultérieurement simplifie la capacité, mais retient sans limite du stock impayé. Encaisser sans option crée le risque de paiement sans unité. L'option limitée réduit ces deux problèmes et exige un worker d'expiration/rapprochement.

Un paiement arrivé après libération n'autorise pas le surbooking : il reste vrai financièrement et devient une anomalie à résoudre. La confirmation manuelle sans paiement, la durée d'option et la politique de remboursement sont des décisions produit à approuver. MVP proposé : Stripe test unique, carte uniquement, paiement total et remboursement intégral autorisé ; Connect et abonnement SaaS ne sont pas inclus.
