# T023 — Récupération de compte

Issue : [#25](https://github.com/ABDOUUisHERE/ai-property-management-saas/issues/25).
Dépendance T022 livrée par la PR #37, fusionnée sur `35a5f1d` après accord
« Oui, fusionne puis continue P03 » et huit checks verts sur `8548949`.

1. Demander un email avec réponse 202 générique, limite par email haché et
   redirection fixée côté serveur vers `/auth/reset` sur l'origine configurée.
2. Livrer un template Supabase avec jeton de récupération dans le fragment du
   lien ; vérifier ce jeton par POST `/verify`, exclusivement de type `recovery`.
   Aucun JWT fournisseur ne devient une session navigateur.
3. Avant PUT `/user`, poser une barrière persistante par sujet : anciennes
   sessions refusées et nouveaux logins bloqués pendant la mutation distante.
   Une réponse ambiguë garde cette barrière jusqu'à une nouvelle récupération.
   Les appels réseau restent hors transaction ; un lease et son propriétaire
   empêchent une réponse tardive de libérer une autre tentative.
4. Prouver le parcours Mailpit réel, refus CSRF/Origin, comptes inconnus, jeton
   réutilisé/expiré, isolation des sujets, rollback et courses login/reset.
   Tester upgrade/downgrade sur PostgreSQL jetable et régénérer OpenAPI/TypeScript.

Le contrat HTTP précède les écrans T031. La fusion du nouveau lot nécessitera
un accord couvrant cette PR ; P04 reste soumise à un nouvel accord.

Références : [API Recover v2.197.0](https://github.com/supabase/auth/blob/v2.197.0/internal/api/recover.go),
[Verify](https://github.com/supabase/auth/blob/v2.197.0/internal/api/verify.go),
[UserUpdate](https://github.com/supabase/auth/blob/v2.197.0/internal/api/user.go),
[variables de template](https://supabase.com/docs/guides/auth/auth-email-templates).
