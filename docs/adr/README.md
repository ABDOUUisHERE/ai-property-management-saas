# Registre des décisions d'architecture

Les six ADRs ont été **acceptés le 2026-11-10** avec la validation utilisateur du cadrage et du backlog. L'ADR 0006 reste conditionnel à un futur accord de déploiement et de budget. L'acceptation porte sur les choix, pas sur des composants déjà réalisés. Les exigences imposées (FastAPI, React, PostgreSQL, monolithe modulaire, Stripe test) sont décrites dans l'architecture sans créer un ADR artificiel pour chacune.

| ADR | Arbitrage | Décision utilisateur |
| --- | --- | --- |
| [0001](0001-auth-authority.md) | Autorité d'identité et frontière de session | D01 |
| [0002](0002-tenant-isolation.md) | Mutualisation des données et défense par RLS | D02 |
| [0003](0003-inventory-concurrency.md) | Protection des séjours et blocages concurrents | D03 |
| [0004](0004-payment-reservation-consistency.md) | Cohérence paiement/séjour et compensation | D04 |
| [0005](0005-durable-async.md) | Livraison durable des effets asynchrones | D10 |
| [0006](0006-hosting-boundary.md) | Hébergement optionnel et frontière Auth | D09 |

En cas d'approbation, changer le statut et noter la date/portée de validation. Si un choix change, conserver la justification et marquer l'ADR remplacé. Les règles détaillées restent dans [le modèle métier](../architecture/domain-data.md) ; les ADRs expliquent les compromis.
