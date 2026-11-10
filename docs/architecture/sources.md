# Sources primaires consultées

Consultation le 2026-11-10. Ces sources vérifient les mécanismes techniques ; l'architecture et les politiques commerciales restent des propositions du projet. Recontrôler versions et compatibilités lors de l'implémentation. Aucun texte externe ne remplace le cahier des charges.

| Source | Point vérifié / usage |
| --- | --- |
| [PostgreSQL — Range Types](https://www.postgresql.org/docs/current/rangetypes.html) | Plages, borne de sortie exclusive, exclusion GiST et combinaison avec `btree_gist` ; décision de protection SQL des réservations |
| [PostgreSQL — Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) | Politiques de lignes, refus par défaut, rôle propriétaire/superuser et `BYPASSRLS` ; définition du rôle runtime et tests |
| [Supabase — JWT](https://supabase.com/docs/guides/auth/jwts) | Validation du jeton et clés attendues ; intégration FastAPI à une seule autorité Auth |
| [Supabase — Sessions](https://supabase.com/docs/guides/auth/sessions) | Sessions/access/refresh ; nécessité de définir les comportements d'expiration et déconnexion |
| [Supabase — Docker](https://supabase.com/docs/guides/self-hosting/docker) | Composition officielle, ressources et services optionnels ; base de l'étude de faisabilité Auth locale |
| [Supabase — Asymmetric Auth Keys](https://supabase.com/docs/guides/self-hosting/self-hosted-auth-keys) | Configuration de clés asymétriques et JWKS en self-hosting ; à tester sur la version locale retenue |
| [Stripe — Webhooks](https://docs.stripe.com/webhooks) | Signature, doublons, ordre non garanti et traitement asynchrone ; inbox et consommateurs idempotents |
| [Stripe — Fulfillment Checkout](https://docs.stripe.com/checkout/fulfillment.md?ui=full-page) | La page de retour n'est pas une preuve suffisante ; vérifier le résultat de paiement et traiter une seule fois |
| [Stripe — Limited Inventory](https://docs.stripe.com/payments/checkout/managing-limited-inventory.md?ui=full-page) | Expiration Checkout manuelle/programmée et fenêtre 30 min–24 h ; choix proposé de 45 minutes |
| [Stripe — Supported Currencies](https://docs.stripe.com/currencies) | Unités mineures, cas particuliers et limites ; validation explicite dans l'adapter de paiement |
| [AWS — ECS/Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) | Conteneurs exécutés en tâches/services avec ressources, réseau et IAM ; fondement de la cible optionnelle API/worker |
| [AWS — RDS PostgreSQL Extensions](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.Extensions.html) | Extensions et permissions dépendent de la version/configuration ; vérifier la cible avant migration |
| [GitHub — Profile Contributions](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference) | Conditions du graphe, email/branche et limites d'affichage ; différencier travail réalisé et contributions visibles |

Inférences du projet : le verrou par unité pour coordonner deux tables, la durée de 45 minutes, les définitions commerciales des revenus, les choix de rôle et la topologie AWS sont nos recommandations. Ils ne sont pas prescrits tels quels par les fournisseurs.
