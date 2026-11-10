# Gestion des locations de courte durée

Vocabulaire de référence du projet. Les règles et choix encore soumis à validation sont décrits dans les documents d'architecture.

## Entreprises et personnes

**Organisation** : Entreprise indépendante qui exploite un portefeuille de locations et possède ses données métier.
_Éviter_ : compte pour désigner une entreprise.

**Tenant** : Frontière d'isolation correspondant à une organisation dans cette plateforme.

**Utilisateur** : Personne disposant d'une identité de connexion à la plateforme.
_Éviter_ : voyageur pour désigner tout utilisateur.

**Membership** : Appartenance d'un utilisateur à une organisation avec un rôle donné.

**Owner** : Membre responsable de l'organisation et de l'attribution des droits les plus sensibles.

**Manager** : Membre chargé de la gestion commerciale et opérationnelle de l'organisation.

**Staff** : Membre chargé des interventions et tâches opérationnelles qui lui sont attribuées.

**Voyageur** : Personne accueillie dans une unité pour un séjour ; sa fiche métier n'implique pas une identité de connexion.

## Hébergement et séjour

**Propriété** : Bien immobilier regroupant une ou plusieurs unités louables dans un même contexte d'adresse, de fuseau et de devise.

**Unité** : Ressource louable individuellement et indivisible pour l'attribution d'un séjour.
_Éviter_ : propriété quand la règle concerne une ressource louable.

**Réservation** : Engagement de séjour d'un voyageur dans une unité pour un intervalle de dates et un prix convenu.

**Blocage de maintenance** : Intervalle pendant lequel une unité est retirée de la disponibilité commerciale pour intervention.

**Option temporaire** : Réservation en attente qui retient une unité pendant une durée limitée avant confirmation.
_Éviter_ : réservation confirmée pour une simple attente de paiement.

**Nuitée vendue** : Nuit d'une unité attribuée à un séjour retenu dans le calcul commercial.

**Arrivée / départ** : Début / fin du séjour dans l'hébergement.
_Éviter_ : Checkout Stripe pour désigner un départ du voyageur.

## Paiements et opérations

**Checkout Stripe** : Parcours de paiement hébergé par Stripe pour un montant associé à une réservation.

**Encaissement** : Paiement effectivement reçu, distinct de la valeur commerciale d'une réservation.

**Remboursement** : Restitution d'un montant encaissé ; elle ne décrit pas à elle seule l'annulation du séjour.

**Tâche de ménage** : Intervention de remise en état d'une unité associée à un séjour ou créée manuellement.

**Ticket de maintenance** : Signalement d'un problème et suivi des interventions nécessaires à sa résolution.
