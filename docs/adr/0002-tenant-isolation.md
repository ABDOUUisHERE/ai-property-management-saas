---
status: accepted
date: 2026-11-10
accepted: 2026-11-10
decision: D02
---

# Schéma métier partagé avec filtres, clés composites et RLS

Proposition : une base PostgreSQL métier et un schéma partagé, `organization_id` sur les tables métier, filtre applicatif, FK composites et politiques RLS sous un rôle runtime restreint. Cette combinaison garde un coût d'exploitation compatible avec une démonstration SaaS et une seule chaîne de migrations, tout en ajoutant une défense contre l'oubli d'un filtre.

Une base ou un schéma par organisation simplifierait certaines frontières physiques, au prix de migrations, pools et sauvegardes multiples. Cette charge n'est pas justifiée par les volumes encore inconnus. Le schéma partagé crée en contrepartie un rayon d'impact commun et impose des tests négatifs systématiques.

Le contexte vient d'une membership vérifiée, pas d'un `organization_id` client. Sa portée est transactionnelle ; rôle migration distinct du rôle API/worker. Identité globale et inbox fournisseur non résolue reçoivent des politiques spécifiques, sans bypass général. RLS n'empêche pas un backend compromis de choisir un autre contexte. Toute exigence future d'isolation physique exige de réévaluer ce choix.
