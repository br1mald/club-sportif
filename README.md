# Club Sportif

Application web de gestion d'un club sportif multi-disciplines : membres, équipes, entraînements, présences, cotisations et compétitions. Backend Flask organisé en blueprints, base de données MySQL, et interface server-rendered (Jinja2).

> Projet académique (L2 GLSI — ESP/UCAD), réalisé en équipe de 2.

## Fonctionnalités

- **Membres** — CRUD complet, recherche par nom/prénom, filtre par équipe, fiche détaillée avec taux d'assiduité et historique des présences
- **Équipes** — affectation des membres, gestion des catégories (junior/senior)
- **Entraînements & présences** — suivi des séances et de la présence des membres
- **Cotisations** — suivi des paiements par saison
- **Compétitions** — gestion des compétitions du club
- **Tableau de bord** — vue récapitulative du club

### Règles métier

- Un membre doit avoir au moins 16 ans pour rejoindre une équipe **senior**
- Un membre ne peut pas appartenir à deux équipes du **même sport** simultanément
- Les changements d'équipe sont historisés (date d'entrée / date de sortie)
- Numéro de licence généré automatiquement (`LIC00001`, `LIC00002`, …)

## Stack

- **Backend :** Python, Flask (blueprints)
- **Base de données :** MySQL (`mysql-connector-python`), requêtes SQL paramétrées
- **Frontend :** templates Jinja2, HTML/CSS

## Architecture

```
app.py              # factory create_app + enregistrement des blueprints
config.py           # configuration (variables d'environnement)
db.py               # connexion MySQL (pattern get_db / close_db)
routes/             # blueprints : membres, entrainements, cotisations, competitions, dashboard
templates/          # vues Jinja2 (base.html, dashboard.html, + un dossier par module)
static/             # CSS / assets
```

## Lancer le projet en local

1. Créer la base de données MySQL `club_sportif` et l'utilisateur `club_app`.

2. Copier `.env.example` vers `.env` et renseigner le mot de passe :

   ```bash
   cp .env.example .env
   # éditer .env : DB_PASSWORD=...
   ```

3. Installer les dépendances et lancer :

   ```bash
   pip install -r requirements.txt        # ou uv sync
   python app.py
   ```

   L'application démarre sur `http://localhost:5000`.

## Auteurs

- Ibrahima Sory Diallo — [@br1mald](https://github.com/br1mald)
- Khadyja Camara - [@khadyjacamara](https://github.com/khadyjacamara)
