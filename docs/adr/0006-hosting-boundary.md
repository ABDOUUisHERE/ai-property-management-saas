---
status: accepted
date: 2026-11-10
accepted: 2026-11-10
decision: D09
---

# Déploiement AWS optionnel avec Auth géré distinct

Si un déploiement est autorisé, proposition : API et worker sur ECS/Fargate, RDS PostgreSQL métier, stockage S3 privé, Redis géré, frontend statique derrière CloudFront et routage API de même origine ; Auth reste un service Supabase géré. Un worker durable et un job de migration distinct motivent ECS plutôt qu'un seul service web simplifié.

Alternatives : App Runner pour réduire l'administration du service web, à comparer en incluant le worker et la connectivité privée ; PostgreSQL Supabase hébergeant aussi le métier pour limiter les services, au prix d'un autre partage de responsabilités. Aucun déploiement hybride supplémentaire n'est nécessaire au MVP local.

Le choix engage budget, région, réseau et responsabilités de restauration. Sans budget/accès, livrer le MVP local vérifié et la procédure proposée sans revendiquer AWS déployé. Avant provisioning, confirmer région et résidence des données, compatibilité PostgreSQL/`btree_gist`, politique Auth et devis d'infrastructure ; ne pas présenter les coûts ou disponibilités de service comme déjà vérifiés.
