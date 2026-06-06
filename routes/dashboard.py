from flask import Blueprint, render_template

from db import get_db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/", methods=["GET"])
def index():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total_membres FROM Membre")
    total_membres = cursor.fetchone()["total_membres"]  # type: ignore

    cursor.execute(
        "SELECT COUNT(*) AS cotisations_impayees FROM Cotisation WHERE Statut = 'impayee'"
    )
    cotisations_impayees = cursor.fetchone()["cotisations_impayees"]  # type: ignore

    cursor.execute("SELECT COUNT(*) AS total_equipes FROM Equipe")
    total_equipes = cursor.fetchone()["total_equipes"]  # type: ignore

    cursor.execute(
        "SELECT COUNT(*) AS prochaines_competitions FROM Competition WHERE Date >= CURDATE()"
    )
    prochaines_competitions_count = cursor.fetchone()["prochaines_competitions"]  # type: ignore

    stats = {
        "total_membres": total_membres,
        "cotisations_impayees": cotisations_impayees,
        "total_equipes": total_equipes,
        "prochaines_competitions": prochaines_competitions_count,
    }

    cursor.execute("""
            SELECT m.Nom, m.Prenom, c.Montant, c.Saison
            FROM Cotisation c
            JOIN Membre m ON c.Num_Licence = m.Num_Licence
            WHERE c.Statut = 'impayee'
            ORDER BY c.Saison DESC
        """)

    membres_impayees = cursor.fetchall()

    cursor.execute("""
            SELECT Nom, Date, Lieu, Type
            FROM Competition
            WHERE Date >= CURDATE()
            ORDER BY Date ASC
        """)

    prochaines_competitions = cursor.fetchall()

    cursor.execute("""
            SELECT m.Nom, m.Prenom, e.Nom_Equipe AS equipe,
            ROUND(COUNT(CASE WHEN p.Present = 1 THEN 1 END) * 100.0 / COUNT(*)) AS taux
            FROM Presence p
            JOIN Membre m ON p.Num_Licence = m.Num_Licence
            JOIN Entrainement en ON p.Entrain_ID = en. Entrain_ID
            JOIN Appartenir a ON a.Num_Licence = m.Num_Licence AND en.Code_Equipe = a.Code_Equipe AND a.Date_Sortie IS NULL
            JOIN Equipe e ON e.Code_Equipe = a.Code_Equipe
            GROUP BY m.Num_Licence, e.Code_Equipe
            ORDER BY taux DESC
            LIMIT 5
        """)

    meilleurs_assidus = cursor.fetchall()

    cursor.close()

    return render_template(
        "dashboard.html",
        stats=stats,
        membres_impayees=membres_impayees,
        prochaines_competitions=prochaines_competitions,
        meilleurs_assidus=meilleurs_assidus,
    )
