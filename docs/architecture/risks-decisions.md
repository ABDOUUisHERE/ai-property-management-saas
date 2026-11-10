# Risques et décisions soumises à validation

L'utilisateur a validé le cadrage, le backlog et les recommandations le 2026-11-10 (« je valide »). D01–D06, D08 et D10 sont acceptées selon les valeurs proposées. D07 accepte le principe de minimisation/conservation, mais ne définit pas une juridiction ou des durées légales. D09 accepte une cible AWS optionnelle, sans autoriser provisioning/dépenses. D11 conserve des hypothèses de recette, sans engagement de SLA. D12 valide le workflow ; nom/visibilité/licence et publication distante restent à finaliser. La réalisation est suivie séparément dans [P01](../progress/phase-01.md).

## Registre des décisions

| ID | Décision / recommandation | Alternative ou question à trancher | Échéance |
| --- | --- | --- | --- |
| D01 | Supabase Auth unique, API façade et cookies protégés ; Auth local Docker | JWT/credentials gérés par notre serveur : davantage de sécurité à implémenter. Valider aussi le mode local et la rotation/révocation | Avant T005/T020 ; [ADR 0001](../adr/0001-auth-authority.md) |
| D02 | Schéma partagé + filtre applicatif + RLS PostgreSQL + FK composites | Schéma/base par tenant : isolation physique mais migrations/exploitation plus coûteuses | Avant T011/T027 ; [ADR 0002](../adr/0002-tenant-isolation.md) |
| D03 | Exclusion sur réservations et verrou commun par unité ; options bloquantes 45 min ; clés création 24 h | Registre d'occupation unifié si writers directs ; durée d'option et conservation à confirmer | Avant T047 ; [ADR 0003](../adr/0003-inventory-concurrency.md) |
| D04 | Confirmation après preuve payée ou confirmation manuelle auditée ; Stripe test unique ; carte, total, remboursement intégral owner | Paiement obligatoire avant toute confirmation ? Acomptes/Connect/hors-ligne et remboursement partiel nécessitent nouveau périmètre | Avant T051/T061 ; [ADR 0004](../adr/0004-payment-reservation-consistency.md) |
| D05 | Matrice owner/manager/staff, 404 invisible/403 interdit, dernier owner protégé | Manager peut-il inviter/rembourser ? Staff voit-il des coordonnées ? | Avant T024/T030 |
| D06 | Pas de portail voyageur authentifié au MVP ; fiche gérée par équipes | Le persona voyageur implique-t-il un portail initial ? Si oui, préciser accès et parcours puis replanifier | Avant validation du périmètre MVP |
| D07 | Rétention par catégorie, anonymisation et purge, pas de durée légale inventée | Juridiction, responsable de données, région, durées et exceptions à préciser | Avant T044/T102 et toute donnée réelle |
| D08 | Prix simples MVP, formule d'arrondi/taxes, revenu hors taxes, métriques par nuit et devise | Définition du revenu brut, taxes inclusives, frais/remises, périodes et départ anticipé à confirmer | Avant T054/T083 |
| D09 | AWS optionnel ECS/Fargate + RDS/S3 ; Auth géré ; région cohérente | Budget, région, domaine et besoin de démo publique ? App Runner si worker/coût favorables | Avant T099 ; [ADR 0006](../adr/0006-hosting-boundary.md) |
| D10 | Ménage au départ par défaut, configurable à confirmation ; une tâche par séjour/type ; outbox PostgreSQL + Celery/Redis | Fréquence/règles de ménage et destinataires email ? Choix d'une file plus simple si preuve équivalente | Avant T019/T073 ; [ADR 0005](../adr/0005-durable-async.md) |
| D11 | Hypothèses de volumes et objectifs provisoires du plan qualité | Budget et objectifs disponibilité/latence/RPO/RTO réalistes ; besoin multilingue, devise de démo et support navigateur | Avant recette de performance et production |
| D12 | Backlog local, neuf jalons MVP, publication après validation, contributions utiles seulement | Compte/nom/visibilité/licence du dépôt, accès Project, stratégie merge et autorisations distantes | Avant T002–T004 |

L'ordre de validation recommandé : D06 pour verrouiller le produit ; D01/D02/D12 pour les fondations ; D03/D04/D05/D08 pour les règles cœur ; D07/D09/D10/D11 avant les livraisons correspondantes. Aucun credential n'est indispensable pour approuver ces documents.

## Registre des risques

Probabilité/impact : faible, moyen, élevé. « Responsable » désigne le module ou rôle de réalisation, pas une personne déjà affectée.

| Risque | Probabilité / impact | Prévention et signal | Preuve / propriétaire |
| --- | --- | --- | --- |
| Fuite cross-tenant par endpoint, jointure ou FK | Moyen / critique | Contexte serveur, RBAC, FK composites, RLS runtime, 404 uniforme | T027–T034 ; organizations + chaque module |
| Contexte A réutilisé pour B dans le pool, cache, job ou onglet | Moyen / critique | Portée transactionnelle, clés tenant, cache retiré, jobs contextualisés | T028, T032, T081, T090 ; plateforme/frontend |
| Bypass RLS par rôle propriétaire/service admin | Moyen / critique | Migration séparée, rôle runtime restreint, exception inbox isolée | T027/T063 ; plateforme |
| Deux confirmations ou réservation sur maintenance | Élevé / critique | Exclusion SQL, verrou unité commun, relecture et tests réels | T049/T050/T059 ; reservations/availability |
| Hold expiré et webhook payé en course | Élevé / élevé | Rapprochement avant libération, commande versionnée, anomalie financière, aucun surbooking | T053/T068 ; payments/reservations |
| Paiement doublé après timeout/événement répété | Moyen / élevé | Tentative persistante, idempotence fournisseur, inbox et unicité métier | T061–T068 ; payments |
| Événements perdus après commit ou Redis vidé | Moyen / élevé | Outbox DB, consommateurs idempotents, file d'échecs et reprise | T019/T069/T076 ; plateforme |
| Double ménage ou email répétitif | Moyen / moyen | Clé séjour/type, reçu consommateur, état et reprise | T074/T080/T082 ; operations/notifications |
| Données erronées par fuseau/DST, arrondi ou devise mixte | Élevé / élevé | Dates civiles, snapshots, décimal, agrégats par devise | T047/T054/T083–T085 ; pricing/reporting |
| PII conservées ou exposées excessivement | Moyen / élevé | Minimisation, vues staff, purge, expurgation logs, politique de sauvegardes | T044/T093/T102 ; guests/plateforme |
| Auth locale complexe ou différente du service géré | Moyen / élevé | Prototype technique ciblé après validation, versions épinglées, recette sessions/JWKS/Compose | T005/T008/T021/T034 ; identity |
| Suppression/archivage détruisant l'historique et les KPI | Moyen / élevé | RESTRICT, archivage, périodes actives et snapshots | T035/T037/T084 ; properties/reporting |
| Déploiement AWS coûteux, permissions excessives ou perte DB | Moyen / élevé | Budget avant provisioning, IaC, OIDC, réseau privé, backup et restauration | T096/T099–T101 ; infra |
| CI verte avec mocks mais intégration réelle cassée | Moyen / élevé | PostgreSQL/worker réels, trois E2E, différencier Stripe réel et fixtures | T059/T072/T082/T098 ; qualité |
| iCalendar présenté comme anti-surbooking instantané | Élevé / élevé en V2 | Limites visibles, imports conflictuels mis en anomalie, aucune promesse de synchro temps réel | T112–T115 ; channels |
| Assistant IA exfiltrant ou inventant des données | Moyen / élevé en V3 | Outils serveur en lecture seule, contrôle tenant, minimisation, citations et évaluation | T116–T120 ; assistant |
| Objectif de contributions prenant le pas sur le produit | Moyen / moyen | Tâches vérifiables, commits cohérents, bilan réel, aucun quota artificiel | T001/T004 ; workflow |

## Scénarios à utiliser en revue

1. Un manager A remplace `guest_id` par celui de B : refus même si l'unité est A et que l'UUID est valide.
2. Deux onglets du même utilisateur sélectionnent A et B : réponses, caches et exports restent dans leur tenant d'origine.
3. Une réservation finit le 12 et une autre commence le 12 : les deux sont valides ; un blocage `[11,13)` entre en conflit avec les deux.
4. Deux owners se retirent simultanément : au moins un reste owner ou une opération échoue.
5. Paiement signé après expiration, unité déjà revendue : paiement enregistré, séjour non réattribué, anomalie et remboursement à décider.
6. Le worker s'arrête après création du ménage mais avant acquittement : reprise sans deuxième tâche.
7. Une propriété change de devise et une unité est archivée : les revenus historiques ne changent pas et les devises restent séparées.
