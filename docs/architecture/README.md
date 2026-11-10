# Architecture proposée — index

Statut : cadrage et recommandations validés le 2026-11-10. Les documents conservent les raisonnements et propositions d'origine ; leur validation ne prouve pas l'implémentation. La réalisation commence en P01 ; voir [le suivi de phase](../progress/phase-01.md). Les paramètres commerciaux/réglementaires encore inconnus restent explicitement ouverts.

| Document | Question traitée |
| --- | --- |
| [Analyse](analysis.md) | Que demande la spécification, que couvre le MVP et comment vérifier sa couverture ? |
| [Système](system-design.md) | Où sont les frontières, dépendances, transactions et sources de vérité ? |
| [Métier et données](domain-data.md) | Quelles règles protègent accès, séjours, argent et historique ? |
| [API et frontend](api-frontend.md) | Quels contrats, parcours et dossiers proposer ? |
| [Qualité et livraison](quality-delivery.md) | Quelles preuves exigera chaque livraison locale ou AWS ? |
| [Risques et décisions](risks-decisions.md) | Quels arbitrages doivent être approuvés et à quel moment ? |
| [Sources primaires](sources.md) | Quelles documentations ont été consultées et pour quelles limites techniques ? |

Les obligations du cahier des charges ne deviennent pas des options dans les ADRs. Les ADRs enregistrent les arbitrages proposés entre plusieurs solutions possibles. La [roadmap](../roadmap.md) utilise les neuf phases demandées dans la session ; sa table de correspondance conserve les phases 0 à 7 du cahier des charges.
