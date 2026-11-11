# Backlog proposé — validation requise

**120 tâches techniques, 12 epics, 36 features et 36 user stories.** Les tâches T001–T104 couvrent la préparation et le MVP ; T105–T115 concernent V2, T116–T120 la V3 facultative. Le backlog a été **validé le 2026-11-10**. Les Issues P01, P02 et P03 sont publiées ; P01 et P02 sont fusionnées, P03 est en cours. L'avancement et les preuves sont suivis dans [P01](../progress/phase-01.md), [P02](../progress/phase-02.md) et [P03](../progress/phase-03.md) ; validation du plan et réalisation des tâches sont distinctes.

Chaque fichier suit Epic → Feature → User Story → Technical Task. Chaque ligne donne identifiant/titre, description, module, priorité, dépendances, critères d'acceptation, tests et complexité. La phase et la version sont explicitement définies par l'en-tête du fichier et s'appliquent à **chaque tâche de ce fichier**. Une dépendance `Txxx` est un préalable de réalisation, non une demande de créer un commit séparé.

Priorités : **P0** = intégrité, sécurité ou fondation bloquante ; **P1** = requis pour livrer le MVP complet ; **P2** = extension V2 ; **P3** = option V3. P1 n'est pas facultatif. Les options AWS, licence et publication distante restent conditionnées à leur décision dédiée, même si leur préparation figure au backlog.

Complexité relative : **1** petite et localisée ; **2** limitée ; **3** plusieurs composants ; **5** intégration ou cas limites importants ; **8** risque élevé, à préciser au démarrage de la tâche. Ce ne sont pas des jours. Une tâche 8 peut nécessiter un découpage utile après exploration, sans fragmentation pour compter des contributions.

| Epic | Phase / version | Tâches | Document |
| --- | --- | --- | --- |
| E01 Environnement et organisation | P01 / MVP | T001–T009 | [Phase 1](phase-01.md) |
| E02 Architecture exécutable | P02 / MVP | T010–T019 | [Phase 2](phase-02.md) |
| E03 Identités et entreprises | P03 / MVP | T020–T034 | [Phase 3](phase-03.md) |
| E04 Biens et voyageurs | P04 / MVP | T035–T046 | [Phase 4](phase-04.md) |
| E05 Disponibilités et réservations | P05 / MVP | T047–T060 | [Phase 5](phase-05.md) |
| E06 Paiements de test | P06 / MVP | T061–T072 | [Phase 6](phase-06.md) |
| E07 Opérations et notifications | P07 / MVP | T073–T082 | [Phase 7](phase-07.md) |
| E08 Dashboard et reporting | P08 / MVP | T083–T091 | [Phase 8](phase-08.md) |
| E09 Livraison et préparation exploitation | P09 / MVP, AWS optionnel | T092–T104 | [Phase 9](phase-09.md) |
| E10 Tarification avancée | PX2 / V2 | T105–T109 | [Extensions V2/V3](extensions.md) |
| E11 Canaux et simulation | PX2 / V2 | T110–T115 | [Extensions V2/V3](extensions.md) |
| E12 Assistant interne | PX3 / V3 | T116–T120 | [Extensions V2/V3](extensions.md) |

## Ordre et travail indépendant

Chemin principal : E01 → E02 → E03 → E04 → E05 → E06 → E07 → E08 → E09. Respecter l'accord entre phases et les dépendances propres aux tâches. Tests et sécurité sont intégrés à chaque epic, puis consolidés en E09.

À l'intérieur d'une phase, peuvent progresser indépendamment après leurs prérequis :

- P01 : conventions/documentation et définition du workflow ; environnement après choix Auth, sans publier de ressources distantes non autorisées.
- P02 : backend T010–T015 et socle frontend T016–T017 ; T018 les réunit.
- P03 : formulaires Auth T031 après contrats, tandis que les contrôles organisation/RLS progressent ; la recette finale T034 attend tout.
- P04 : biens/unités et voyageurs ; stockage/photos après modèle de biens. Les tâches de reporting historique ne doivent pas être oubliées dans l'archivage.
- P05 : pricing minimal T054 et interfaces T057/T058 après contrats ; réservation/maintenance et expiration ont un ordre strict documenté.
- P06 : UI T071 après contrat paiement ; signature/inbox avant consommateurs, remboursement après preuve d'encaissement.
- P07 : UI opérations et transport email après contrat ; automatisation ménage après clés et événement de départ fiables.
- P08 : définitions/SQL et interfaces après contrat commun ; isolation/export avant recette complète.
- P09 : documentation/accessibilité et durcissement en parallèle des preuves de restauration ; AWS seulement si option autorisée.
- V2 : tarifs et simulateur de canaux sont indépendants après MVP. V3 n'exige pas V2 ; aucune dépendance du MVP vers IA.

Cette carte décrit les possibilités techniques, pas une autorisation de lancer des sous-agents. Les tâches sont proposées pour des incréments cohérents : plusieurs tâches liées peuvent partager une PR ; une tâche ne correspond pas nécessairement à une contribution visible sur GitHub.

## Passage futur aux Issues

Après validation, conserver les IDs locaux dans titres/corps, reporter critères/tests/dépendances, associer la phase au milestone et les champs au Project si disponible. Vérifier chaque Issue créée et enregistrer son URL réelle. Éviter les doubles publications et les Issues vides. Le workflow détaillé et le modèle de corps se trouvent dans [l'organisation GitHub](../github-workflow.md).
