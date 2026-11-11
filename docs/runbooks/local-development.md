# Développement local — dépendances P01 et bootstrap P02

Le root `pyproject.toml` et `uv.lock` concernent l'outillage d'infrastructure.
Le bootstrap démarre désormais aussi API, interface, worker, dispatcher et
migration. Leur détail figure dans [le runbook applicatif](application-development.md).
Les sections ci-dessous décrivent les dépendances P01 et leurs contrôles.

## Prérequis

Git, uv et Docker Engine/Compose avec moteur **Linux** actif. Sous Windows, Docker Desktop avec WSL2 doit être démarré et ne pas être en pause. Python 3.12 est sélectionné par `.python-version` ; uv peut installer l'interpréteur requis. Node n'est pas nécessaire pour cette phase.

Prévoir les ressources nécessaires aux services déjà lancés sur la machine ; le projet ne redémarre ni ne supprime les autres stacks. Les commandes s'exécutent depuis la racine du dépôt, y compris si son chemin contient des espaces.

## Initialiser et démarrer

```powershell
uv sync --locked
uv run python scripts/dev.py init
uv run python scripts/dev.py doctor
uv run python scripts/dev.py up
uv run python scripts/dev.py smoke
```

`init` génère des secrets distincts et une clé privée ES256 dans `.env`, ignoré par Git. Une seconde exécution préserve **exactement** les clés existantes et refuse un fichier invalide. Aucune valeur secrète n'est affichée. Sous POSIX, la création demande le mode 0600 ; sous Windows, les ACL du dossier utilisateur s'appliquent. Ne pas partager `.env`.

`up` utilise `docker compose up --build --wait --wait-timeout 180` et attend les sondes. Après génération de `.env`, `docker compose up --build` est également utilisable directement. Aucun compte Supabase distant, AWS ou Stripe n'est requis.

`smoke` refuse les URLs distantes et `APP_ENV` autre que `local`. Il vérifie : connexions et privilèges PostgreSQL runtime/migration ; Redis authentifié ; écriture et lecture S3 signée avec refus anonyme ; inscription Auth, email réellement reçu dans Mailpit, confirmation, login, signature ES256/JWKS, refresh et révocation du refresh après logout. L'utilisateur et l'objet de test fictifs sont supprimés dans les blocs de nettoyage ; les emails locaux restent soumis à la limite Mailpit. Le bucket local est créé s'il manque.

Cela ne prouve ni la façade de session FastAPI, ni RLS métier, ni les réservations/paiements, qui n'existent pas encore. Les JWT d'accès fournisseur déjà émis peuvent rester valides jusqu'à expiration : la révocation immédiate de la future façade sera testée en P03.

La vérification JWT de cette recette autorise 5 secondes de décalage entre l'horloge Windows et celle du moteur Docker. Signature, algorithme, issuer et audience restent obligatoires ; un token daté d'une minute dans le futur est refusé par un test dédié. Les sondes PostgreSQL utilisent TCP pour attendre la fin de l'initialisation, sans confondre le serveur Unix temporaire du bootstrap avec la base prête à recevoir Auth.

## Services accessibles par défaut

| Service | Adresse locale | Usage |
| --- | --- | --- |
| PostgreSQL métier | `127.0.0.1:15432` | Base `property_management`, rôles `pms_app` et `pms_migrator` distincts |
| Supabase Auth | `http://127.0.0.1:19999` | Dépendance Auth ; endpoints directs `/health`, `/signup`, `/token`, `/.well-known/jwks.json` |
| Redis | `127.0.0.1:16379` | Authentification nécessaire |
| Mailpit | `http://127.0.0.1:18025` | Messages de test uniquement ; SMTP interne, aucun envoi réel |
| S3 compatible | `http://127.0.0.1:19000` | RustFS, credentials générés, console désactivée |

La base Auth n'a pas de port hôte. Chaque port publié est limité à `127.0.0.1`. Les ports sont personnalisables dans `.env` avant démarrage ; si le port Auth change, adapter aussi `AUTH_EXTERNAL_URL`. Le projet par défaut est `pms_dev` ; personnaliser `COMPOSE_PROJECT_NAME` avant de créer les volumes d'un deuxième environnement.

## Contrôles locaux et CI

```powershell
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_repository.py
uv run pytest
uv run python scripts/scan_secrets.py
docker compose config --quiet
```

Le scanner télécharge Gitleaks depuis sa release officielle, vérifie un checksum épinglé, éprouve sa détection avec une fixture synthétique, puis analyse une copie des fichiers suivis/éligibles pour Git. Les fichiers locaux ignorés ne sont pas copiés ; un secret accidentellement suivi reste analysé. Aucune donnée du dépôt n'est envoyée au scanner distant. Le téléchargement initial demande Internet, ensuite l'archive vérifiée est réutilisée.

La CI reprend ces contrôles sur Ubuntu et ajoute le démarrage/smoke des six services. Le workflow n'est exécuté sur GitHub qu'après publication autorisée ; un passage local n'est pas un résultat GitHub Actions.

## Arrêt, reprise et diagnostic

```powershell
uv run python scripts/dev.py status
uv run python scripts/dev.py stop
uv run python scripts/dev.py up
```

L'arrêt conserve les volumes. Pour éprouver le redémarrage sans modifier les autres stacks : `docker compose restart`, attendre les sondes avec `uv run python scripts/dev.py up`, puis relancer `smoke`. `docker compose ps --all` donne les états sans afficher les variables secrètes. Éviter `docker compose config` sans `--quiet` sur `.env` réel et les dumps d'inspection d'environnement.

Pour valider les seules dépendances dans une stack distincte, initialiser avec
`uv run python scripts/dev.py init --env-file .local/validation.env`, puis choisir
un autre `COMPOSE_PROJECT_NAME`, cinq ports distincts et l'URL Auth correspondante.
Lancer uniquement les six dépendances avec
`docker compose --env-file .local/validation.env up -d --wait postgres auth-db auth redis mailpit storage`,
puis `uv run python scripts/dev.py smoke --env-file .local/validation.env`.
Le démarrage complet P02 utilise aussi les ports API/UI fixes : ne pas lancer
deux applications simultanément sur ces mêmes ports.

Si un service est unhealthy, consulter localement ses logs en gardant leurs données sensibles hors des échanges. Vérifier Docker actif, ports disponibles, espace disque, ressources et cohérence des credentials avec les volumes. Les init PostgreSQL ne sont exécutés que sur une base neuve : changer les passwords dans `.env` n'effectue pas une rotation SQL.

Le script ne supprime aucun volume et ne régénère pas les clés existantes.
Une remise à zéro exige d'identifier le projet et ses volumes et de préparer
une procédure ciblée. Les migrations des primitives outbox existent en P02 ;
le seed et les migrations métier arrivent avec les fonctionnalités suivantes.
