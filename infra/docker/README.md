# Dépendances locales — P01

La composition racine contient uniquement des services d'infrastructure. FastAPI, React, Alembic et les workers applicatifs seront ajoutés en P02 ; aucune fonctionnalité métier n'est simulée ici.

## Supabase Auth minimal

Configuration adaptée depuis la composition officielle Supabase au commit [`79763687f7e5227ed961c1c86c3444b2b59c8a68`](https://github.com/supabase/supabase/blob/79763687f7e5227ed961c1c86c3444b2b59c8a68/docker/docker-compose.yml), image GoTrue `v2.197.0`. Documentation : [Auth auto-hébergé](https://supabase.com/docs/guides/self-hosting/auth/config), [clés asymétriques](https://supabase.com/docs/guides/self-hosting/self-hosted-auth-keys).

Seuls Auth, sa base PostgreSQL isolée et Mailpit sont nécessaires. Studio, PostgREST, Realtime, Storage Supabase et gateway ne sont pas installés : l'API métier passera exclusivement par FastAPI. Auth est joignable directement à la racine de son URL locale, sans préfixe `/auth/v1` ni clé de gateway. L'issuer local est explicitement configuré ; le backend utilisera l'issuer de son environnement.

Une clé ES256 locale générée signe les JWT, le JWKS ne doit exposer que la partie publique. Une valeur symétrique est également configurée car le serveur la requiert ; les tests doivent vérifier que les tokens utilisateurs sont effectivement ES256. Les clés ne sont jamais copiées dans ce dépôt. Confirmation d'email activée ; Mailpit capte les messages, sans envoi à un destinataire réel.

L'init Auth crée le schéma requis et son rôle propriétaire restreint, puis GoTrue applique ses propres migrations. Un rôle de compatibilité `postgres`, NOLOGIN et sans privilège administrateur, reçoit les grants attendus par ces migrations ; il ne sert pas de compte de connexion. Cela ne remplace pas Alembic : les migrations des tables métier seront développées en P02. Deux instances PostgreSQL et deux réseaux séparent identité et métier. Le rôle runtime métier ne possède ni table ni privilège superuser/bypass RLS.

## Stockage, Redis et reproductibilité

RustFS fournit le service S3-compatible de développement ; son adapter sera testé via boto3. Il ne détermine pas le fournisseur de production. Voir [installation officielle](https://docs.rustfs.com/en/installation) et [sondes](https://docs.rustfs.com/en/operations/status-check). La console n'est pas exposée ; accès S3 par credentials générés, objets privés par défaut.

Redis est authentifié, persistant et distinct de toute garantie d'inventaire. Mailpit conserve uniquement les emails locaux fictifs. Les ports publiés sont liés à `127.0.0.1` ; les deux réseaux bridge sont distincts, sans revendiquer une isolation réseau de production.

Chaque image est verrouillée par digest de manifeste multiarchitecture, résolu depuis le registre le 2026-11-10. Toute mise à jour exige relecture des notes de version et nouvelle recette. Les init scripts PostgreSQL s'appliquent uniquement à un volume neuf ; modifier `.env` ne change pas les passwords d'une base déjà initialisée. Le runbook prévoit les opérations de reprise sans effacer les volumes implicitement.
