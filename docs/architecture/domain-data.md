# Règles métier et modèle de données proposés

Les règles marquées « proposition » doivent être validées via D01–D12. Les obligations explicites de la spécification restent impératives. Les noms sont cohérents avec le [glossaire](../../GLOSSARY.md).

## Invariants d'accès et rôles

Chaque opération métier possède un acteur, une organisation autorisée et une permission sur l'action **et** la ressource. Politique HTTP proposée : 401 sans session valide ; 404 pour une ressource étrangère ou inexistante ; 403 pour une action interdite sur une ressource visible du tenant. Même politique dans les téléchargements et exports. Les listes ne révèlent ni compte, ni existence d'identifiants étrangers.

Proposition D05 :

| Action | Owner | Manager | Staff |
| --- | --- | --- | --- |
| Lire biens et calendrier | Oui | Oui | Vue opérationnelle limitée |
| Modifier biens, unités et prix | Oui | Oui | Non |
| Gérer voyageurs et réservations | Oui | Oui | Informations de séjour utiles à ses tâches uniquement |
| Accéder aux coordonnées voyageurs | Oui | Oui | Masquées par défaut ; besoin explicite à valider |
| Créer Checkout / consulter paiements | Oui | Oui | Non |
| Demander un remboursement | Oui | Non par défaut | Non |
| Créer/attribuer des tâches | Oui | Oui | Non ; signaler une maintenance autorisé |
| Changer statut/notes d'une tâche | Oui | Oui | Ses tâches attribuées seulement |
| Gérer invitations et rôles | Oui | Non par défaut | Non |
| Consulter reporting / audit | Oui | Oui / audit métier limité | Non |
| Anonymiser un voyageur / transférer ownership | Oui | Non | Non |

Conserver au moins un owner actif : transfert, retrait et changement de rôle vérifiés dans une transaction verrouillant l'organisation. Empêcher une élévation via payload de profil ou invitation. Invitations à durée limitée, jeton stocké haché, destinataire vérifié, acceptation atomique, révocation et unicité membership. Un voyageur n'est pas automatiquement membre.

## Propriétés, unités, voyageurs et conservation

- Une unité appartient à une seule propriété du même tenant ; la propriété porte un fuseau IANA valide et une devise ISO supportée. Capacité strictement positive ; nombre de voyageurs de la réservation compatible.
- Une unité archivée n'accepte plus de nouvelles réservations. Proposition : interdire son archivage tant qu'existent des séjours/options futurs actifs. La présence d'historique interdit la suppression destructrice ; les références historiques utilisent `RESTRICT`.
- Modifier la devise ou le fuseau d'une propriété ayant des réservations impose une règle explicite : proposition d'interdiction pour les séjours actifs et conservation des valeurs figées sur les séjours passés. Une modification de capacité ne doit pas invalider silencieusement une réservation future.
- Une fiche voyageur est locale à l'organisation, même si l'adresse email existe ailleurs. Email non unique globalement ; téléphone facultatif, préférences minimisées. Aucun document d'identité requis au MVP.
- Photos privées : taille/type contrôlés, nom d'objet généré, accès après RBAC, nettoyage des uploads orphelins. Ne pas charger une URL distante arbitraire fournie par le client.
- Proposition D07 : anonymiser les données d'identification lorsque la conservation n'est plus nécessaire et permise ; garder les faits historiques non identifiants utiles. Les durées, bases et exceptions dépendent de la juridiction à préciser. Ne pas prétendre qu'une durée arbitraire est légalement correcte.
- Les payloads Stripe conservés sont réduits au nécessaire ; pas de payload brut dans les logs. Définir purge des sessions, invitations, clés d'idempotence, événements, exports, objets et sauvegardes. Un audit append-only n'est pas un droit de conservation illimitée de données personnelles.

## Dates et disponibilité

Les nuitées utilisent des **dates civiles** `start_date`/`end_date`, pas des minuits UTC : intervalle `[check_in, check_out)`, `start_date < end_date`. Les instants techniques, paiements, expiration et arrivée/départ effectifs utilisent `timestamptz` UTC. Le fuseau de la propriété donne les dates locales et horaires de ménage ; le changement d'heure ne transforme pas une nuitée en durée de 24 heures fixe. Deux séjours `[10,12)` et `[12,14)` sont adjacents et compatibles.

Proposition D03 : `draft` ne bloque pas ; `pending` est une option limitée ; `confirmed`, `checked_in` et `checked_out` protègent le séjour, y compris son historique ; `cancelled` libère la disponibilité commerciale. Les blocages maintenance actifs retirent aussi la capacité.

**Garantie SQL sur les réservations.** Prévoir une contrainte d'exclusion GiST associant organisation, unité et `daterange(start_date, end_date, '[)')` avec chevauchement interdit pour les états bloquants. `btree_gist` permet l'égalité des identifiants avec la plage. La contrainte doit couvrir les changements d'état et de dates, pas seulement INSERT. Le mécanisme est documenté par [PostgreSQL](https://www.postgresql.org/docs/current/rangetypes.html). L'extension et les privilèges disponibles chez l'hébergeur sont à prouver.

**Protection des blocages et modifications croisées.** Une exclusion sur `reservations` ne vérifie pas une autre table. Toute mutation d'inventaire, y compris maintenance, option, confirmation, annulation, archivage et changement de dates/unité :

1. Ouvrir une transaction avec le contexte tenant.
2. Verrouiller la ligne `units` de chaque unité concernée (`FOR UPDATE`), dans l'ordre stable des identifiants en cas de déplacement.
3. Relire après acquisition les séjours bloquants et blocages maintenance ; vérifier capacité, état et intervalle.
4. Écrire la mutation, l'audit et l'outbox ; committer. En conflit, rollback et réponse 409 stable.

Isolation READ COMMITTED avec relecture après le verrou ; aucune décision sur une simple lecture de calendrier préalable. Tous les writers supportés passent par ce protocole, y compris workers/imports/seed. La contrainte SQL protège les chevauchements de réservations même en cas d'erreur applicative ; la règle inter-tables repose en plus sur ce protocole commun et ses tests. L'accès DML hors application est réservé aux procédures contrôlées d'exploitation. Si de nouveaux writers directs apparaissent, renforcer par un registre commun d'occupation ou des procédures SQL avant de les autoriser. Aucun lock Redis n'est une garantie d'inventaire.

Une option expirée reste bloquante tant que sa transition persistée n'a pas libéré l'unité : pas de prédicat d'index dépendant de `now()`. Worker d'expiration et rapprochement sont nécessaires dès la phase 5. Une indisponibilité du worker peut réduire la capacité vendable, jamais autoriser une double réservation.

## Machine à états des séjours

| État source | État cible | Garde / effet proposés |
| --- | --- | --- |
| draft | pending | Dates, capacité et devis valides ; option et expiration persistées sous verrou |
| draft | confirmed | Confirmation manuelle owner/manager explicitement autorisée, motif et prix figés ; paiement restant visible |
| draft | cancelled | Abandon explicite |
| pending | confirmed | Commande serveur autorisée ; webhook payé rapproché et option encore valide, ou décision manuelle auditée |
| pending | cancelled | Annulation ou expiration sûre ; annuler/rapprocher un Checkout actif avant de revendre |
| confirmed | checked_in | Action owner/manager ; date locale d'arrivée atteinte, exceptions documentées |
| checked_in | checked_out | Action owner/manager ; départ effectif enregistré, événement ménage |
| confirmed | cancelled | Selon politique commerciale à valider ; remboursement distinct, pas implicite |

`checked_out` et `cancelled` sont terminaux au MVP. Toute transition absente est refusée. Le départ anticipé termine le séjour effectif sans réécrire automatiquement son prix ni ses dates contractuelles ; libérer les nuits restantes demande une action explicite future. Proposition : modification de dates/unité autorisée seulement en `draft` ou `pending` sans Checkout actif. Pour un séjour confirmé, l'extension/modification commerciale est à reporter ou à spécifier séparément, jamais un PATCH libre.

Les commandes répétées de même transition renvoient un résultat stable si l'état final correspond déjà ; elles n'émettent pas un second événement. Une version de ressource/condition d'écriture protège les formulaires concurrents contre les mises à jour perdues.

## Idempotence des créations

Clé requise pour création de réservation ; scope `(organization_id, actor_id, operation, key)`, hash canonique du payload, état en cours/terminé et résultat persistant. Même clé et même payload : même réservation et réponse ; payload différent : 409. Deux requêtes simultanées convergent via contrainte unique, pas par un cache. La création et le résultat idempotent sont committés ensemble ; une transaction avortée ne laisse pas un succès fantôme. Proposition D03 : conservation minimale 24 h pour ces clés, réponse documentée au-delà ; la durée doit être validée avant implémentation. Ne pas confondre cette politique avec la fenêtre d'idempotence du fournisseur.

## Prix et argent

Pricing minimal **MVP** : tarif de base par unité/nuit, frais et taxes configurés simplement, remise autorisée et calcul de devis déterministe. F07 ajoute seulement les saisons, jours de semaine, minimum de séjour et règles avancées. Une réservation fige les lignes et versions du calcul ; modifier le tarif futur ne modifie pas l'historique.

Montants entiers en unités mineures, devise explicite, calcul intermédiaire décimal ; aucune somme monétaire en float. Respecter l'exposant de devise, qui n'est pas toujours 2. Proposition D08 : sous-total = nuitées + frais ; remise plafonnée appliquée avant taxes ; taxes exclusives calculées par ligne imposable, arrondi half-up à l'unité mineure, somme finale exacte. La fiscalité est paramétrable et ne vaut pas certification fiscale. Définir si une taxe s'applique par nuit/personne ou au séjour : MVP proposé pourcentage par ligne et frais fixes au séjour ; autres règles à spécifier.

Une réservation utilise la devise de son unité/propriété ; aucune conversion FX au MVP. Les agrégats financiers sont séparés par devise. Frais/taxes/remises et total sont validés côté serveur ; le client ne fournit pas un total faisant autorité. Réservations à montant zéro : confirmation manuelle tracée, pas de Checkout Stripe ; montants non supportés par Stripe refusés avant appel. L'adapter traduit explicitement les unités métier vers les unités attendues par Stripe et contrôle ses cas particuliers et limites ; ne pas supposer qu'une multiplication uniforme par 100 suffit. [Source : devises Stripe](https://docs.stripe.com/currencies).

## Paiements et options temporaires

Proposition D04 : un seul compte Stripe de test pour la démonstration, une tentative active par réservation, paiement total en une fois, carte de test uniquement ; pas d'abonnements, acomptes, paiements différés, Connect ou transferts aux propriétaires. Pour un séjour non confirmé, `pending` réserve la capacité avant création du Checkout. La durée proposée est **45 minutes**, à aligner avec `expires_at` et les limites du fournisseur ; Stripe documente une expiration programmée entre 30 minutes et 24 heures. [Source : inventaire Checkout](https://docs.stripe.com/payments/checkout/managing-limited-inventory.md?ui=full-page).

Si une option existante n'a plus une durée résiduelle suffisante pour ouvrir Checkout, refuser par 409 et demander une nouvelle option explicite sous verrou ; ne pas allonger silencieusement un blocage. Un séjour déjà confirmé manuellement et encore impayé peut aussi être réglé par Checkout : sa confirmation protège déjà l'unité, et l'expiration de cette tentative ne doit pas annuler le séjour. Ces deux modes d'éligibilité sont testés séparément.

Séquence :

1. Sous transaction, autoriser la réservation et créer la tentative avec une clé fournisseur stable ; pour un séjour non confirmé, figer le devis et retenir l'option ; pour un séjour déjà confirmé, utiliser son prix et son attribution existants.
2. Hors transaction, créer la session Stripe avec cette clé ; persister sa correspondance par une seconde transaction avec contrôle de version. Si la réponse est perdue, reprendre la même tentative ; ne pas créer un nouveau paiement au hasard.
3. Le webhook signé rapproche compte, mode test, session/PaymentIntent, réservation locale, montant et devise. Persister l'inbox avant accusé de réception ; un événement déjà connu renvoie 2xx sans supprimer un traitement en attente. Échec de persistance = erreur réessayable.
4. Le consommateur met à jour le paiement et demande la confirmation de séjour dans une transaction locale cohérente ; un séjour déjà confirmé conserve son état, les effets/outbox sont uniques. Un refus de confirmation doit produire une anomalie persistante, pas faire disparaître le paiement vérifié ; traiter tout conflit SQL avec rollback/savepoint approprié avant de persister sa résolution. Seul un résultat de paiement vérifié vaut `paid` ; le redirect n'est qu'une page de statut. [Source : fulfillment Checkout](https://docs.stripe.com/checkout/fulfillment.md?ui=full-page).
5. Le worker expire/réconcilie les sessions hors transaction réseau, puis applique le résultat sous verrou et contrôle de version. Ne pas libérer une unité si un paiement actif reste ambigu ; placer en rapprochement et alerter.

La vérification du webhook porte sur le corps HTTP brut, la signature et une tolérance temporelle ; déduplication durable par event ID. Les événements peuvent être répétés et désordonnés : utiliser aussi les invariants métier et la correspondance fournisseur pour empêcher les effets doubles et les régressions d'état. [Source : webhooks Stripe](https://docs.stripe.com/webhooks).

`payment_pending → paid | failed`, `failed → payment_pending` par nouvelle tentative autorisée, `paid → refunded` après remboursement intégral confirmé. Le remboursement est un objet/commande avec état de demande distinct ; un appel réseau réussi n'autorise pas une régression depuis `refunded`. MVP proposé : remboursements intégraux seulement, réservés owner ; le montant cumulé ne peut dépasser l'encaissé. La preuve de remboursement vient du rapprochement Stripe, et non d'une simple intention locale.

Cas de course obligatoire : si une preuve valide de paiement arrive après libération/annulation, enregistrer l'argent réellement reçu, **ne pas** réattribuer une unité occupée et créer une anomalie consultable pour décision de remboursement. Une réservation peut donc être `cancelled` avec un paiement `paid` en attente de résolution. Le statut financier n'est pas le statut du séjour. L'annulation seule ne déclenche pas automatiquement un remboursement.

## Opérations et notifications

Proposition D10 : règle par organisation, déclencheur unique `checked_out` par défaut ; option `confirmed` pour planifier le ménage à la date de départ. Clé métier unique `(organization_id, reservation_id, task_type)` pour le cycle ménage du séjour ; répéter confirmation ou départ met à jour une même tâche si nécessaire. Une annulation retire une tâche planifiée non commencée ; une intervention terminée reste historique. Une réservation confirmée manuellement déclenche la même règle.

Statuts tâches proposés : `todo → in_progress → done`, `todo|in_progress → cancelled`, réouverture par manager avec audit. Tickets : `open → in_progress → resolved → closed` ; réouverture contrôlée. Affectation à une membership active du tenant ; retrait d'un membre réattribue ou signale ses tâches. Un ticket ne bloque pas automatiquement l'unité : blocage maintenance explicite sous protocole d'inventaire.

La création de tâche, sa notification et leurs reprises sont séparées. Retry borné uniquement pour opérations sûres ; file d'échecs consultable et reprise autorisée/auditée. L'email simulé local est une intégration réelle au serveur de test, pas une preuve d'envoi en production.

## Définitions des indicateurs proposées

Proposition D08, à valider avec un exemple chiffré en T083. Période de dates `[début, fin)` évaluée dans le fuseau de chaque propriété ; sélectionner les nuitées qui intersectent la période. Réservations par statut : compter les séjours intersectant la période, en précisant que ce n'est pas un décompte par date de création.

- Nuitées disponibles : unités actives pour chaque date de la période, moins les nuits de maintenance ; conserver les périodes d'activation/archivage pour ne pas recalculer tout l'historique selon l'état actuel.
- Nuitées vendues : nuits des séjours `confirmed`, `checked_in`, `checked_out` intersectant la période ; options exclues. Pour une période future, il s'agit d'occupation prévisionnelle.
- Taux d'occupation = nuitées vendues / nuitées disponibles. Dénominateur nul : valeur nulle documentée, pas division par zéro.
- Revenu hébergement : lignes de nuitées après remises attribuées à ces nuits, hors frais et taxes. Allocation par nuit figée au devis ; reliquats d'arrondi distribués de façon déterministe.
- Revenu brut commercial : hébergement + frais après remises, hors taxes, pour les séjours retenus. Frais de séjour attribués à la date d'arrivée pour les périodes ; cette convention doit être visible dans l'export. Ce n'est pas l'encaissement Stripe.
- ADR = revenu hébergement / nuitées vendues ; RevPAR = revenu hébergement / nuitées disponibles. Résultats monétaires regroupés par devise, sans somme EUR + MAD.
- Encaissements et remboursements : indicateurs distincts selon leurs instants de transaction, avec filtre de période explicite. Les remboursements ne réécrivent pas rétroactivement le prix contractuel.

## Tables et intégrité proposées

| Groupe | Tables | Points d'intégrité / conservation |
| --- | --- | --- |
| Identité | `users`, `auth_sessions` | Sujet Auth unique ; session opaque hachée, tokens fournisseur chiffrés, révocation locale ; pas de second mot de passe |
| Organisations | `organizations`, `memberships`, `invitations` | `organizations.id` est la racine tenant ; membership unique `(organization_id,user_id)` ; dernier owner protégé |
| Biens | `properties`, `units`, `property_photos`, `unit_active_periods` | Tenant obligatoire, références composites ; périodes utiles au reporting historique |
| Voyageurs | `guests` | Tenant obligatoire ; anonymisation compatible avec l'historique |
| Séjours | `reservations`, `reservation_price_lines`, `reservation_events` | Dates/prix/devise/checks ; exclusion ; état et version ; snapshot du fuseau/prix |
| Disponibilité | `availability_blocks` | Unité du tenant, dates valides, statut actif ; protocole de verrou commun |
| Tarifs | `rate_rules` | MVP limité aux règles simples ; évolution avancée V2 ; version du devis |
| Paiements | `payment_records`, `payment_attempts`, `refund_requests`, `webhook_events` | IDs Stripe uniques dans le compte/mode ; montant/devise figés ; aucune carte |
| Opérations | `tasks`, `task_events`, `maintenance_tickets`, `maintenance_ticket_events`, `maintenance_attachments`, `operation_settings` | Affectation au tenant, clé ménage unique, historique d'état et d'intervention |
| Notifications | `notifications`, `notification_attempts` | État, prochaines tentatives, erreur expurgée, clé métier |
| Fiabilité | `idempotency_keys`, `outbox_events`, `consumer_receipts`, `job_failures` | Scope tenant, unicité et état ; rétention explicitée |
| Audit | `audit_events` | Tenant, acteur/pseudonyme, action, ressource, instant, corrélation ; contenu minimal |

Toutes les tables métier portent `organization_id NOT NULL`. Exceptions explicites : `users` global et `auth_sessions` rattachée à l'identité globale, sous politique spécifique ; `organizations.id` racine ; inbox Stripe d'entrée technique initialement sans tenant connu. `webhook_events.organization_id` est nullable uniquement en état non résolu/quarantaine ; ces lignes sont invisibles aux utilisateurs et traitées par une capacité technique dédiée à droits minimaux, sans autoriser le worker général à bypasser RLS. Une fois résolues, elles sont rattachées immuablement à l'organisation. Payload non résolu expurgé et rétention courte à fixer.

Pour chaque référence tenant, utiliser une unicité cible `(organization_id,id)` et une FK composite, par exemple réservation → unité/voyageur et tâche → membership. UUID seul n'est pas une autorisation. Index courants commencent par l'organisation et les filtres utilisés : état/dates/unité pour séjours, échéance/assignation pour tâches, date pour audit. Vérifier les plans plutôt qu'indexer chaque colonne. Les FK historiques sont restrictives ; le cascade ne concerne que les dépendances techniques supprimables dont la rétention est explicitement décidée.
