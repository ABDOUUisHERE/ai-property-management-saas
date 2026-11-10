---
status: accepted
date: 2026-11-10
accepted: 2026-11-10
decision: D01
---

# Une seule autorité d'authentification, Supabase Auth

Proposition : déléguer identifiants, vérification d'email et récupération de compte à Supabase Auth ; conserver uniquement le profil et les memberships dans la base métier. FastAPI reste la façade attendue par l'API et contrôle les permissions en base à chaque requête. Cela évite de développer une seconde gestion de mots de passe tout en préservant l'indépendance du modèle métier.

Alternative réelle : gérer credentials, JWT, renouvellement, révocation et récupération côté FastAPI. Le démarrage Compose serait plus simple, mais la responsabilité de sécurité et de maintenance serait sensiblement plus grande. Aucun mode hybride de credentials ne sera installé.

Conséquences : dépendance au fournisseur pour les sessions ; prévoir adapter Auth, lien immuable sujet/profil, restauration cohérente et test de clés/rotation. Proposition de transport : cookie opaque protégé derrière façade même origine et protection CSRF ; session locale révocable, tokens fournisseur chiffrés côté serveur et renouvellement coordonné. Cela ajoute une table technique et une clé de chiffrement à exploiter, tout en évitant d'exposer les refresh tokens au JavaScript client. Une composition Auth locale reproductible doit être prouvée avant de considérer les fondations terminées. Si elle échoue, réviser cet ADR avec l'utilisateur avant de construire le métier.
