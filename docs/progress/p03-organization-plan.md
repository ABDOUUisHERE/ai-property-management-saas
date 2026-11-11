# T024 — Organisation et premier owner

Issue : [#26](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/26).
Dépendances T020/T011 livrées. Lot P03 autorisé ; publication dans la PR #38,
avec T023 pour former le prochain incrément identité/organisation.

1. Ajouter organisations et memberships sous RLS forcée, avec rôle runtime
   restreint et appartenance unique `(organization_id, user_id)`.
2. Créer organisation + premier owner atomiquement ; une référence différée
   interdit le commit d'une organisation sans membership du créateur. La politique
   d'insertion owner exige l'organisation créée dans la transaction courante ;
   aucune voie de bootstrap ne permet de rejoindre une organisation existante.
3. Exposer création idempotente par UUID de requête et liste de ses organisations,
   après résolution de session. Un payload ne peut fournir ni acteur ni rôle.
   Résoudre le sélecteur d'organisation après appartenance active actuelle,
   avec contexte local à la transaction et sans tenant actif global.
4. Prouver répétition/concurrence, rollback, listes A/B, refus SQL sans contexte,
   acteur étranger et pool A → B sur PostgreSQL réel ; vérifier API et migration.

Les invitations, changements de rôle, audit sensible et permissions de ressources
seront livrés par T025–T030. Ce lot ne prétend pas terminer toute l'isolation
des futurs modules métier ni permettre la gestion des membres.
