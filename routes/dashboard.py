from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/", methods=["GET"])
def index():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(" SELECT COUNT(*) AS total_membres FROM Membre ")

    total_membres = cursor.fetchone()["total_membres"]  # type: ignore

    cursor.execute(
        "SELECT COUNT(*) AS cotisations_impayees FROM Cotisation WHERE statut = 'impayee'"
    )
    cotisations_impayees = cursor.fetchone()["cotisations_impayees"]  # type: ignore

    cursor.execute("SELECT COUNT(*) AS total_equipes FROM Equipe")
    total_equipes = cursor.fetchone()["total_equipes"]  # type: ignore

    cursor.execute(
        "SELECT COUNT(*) AS prochaines_competitions FROM Competition WHERE date >= CURDATE()"
    )
    prochaines_competitions_count = cursor.fetchone()["prochaines_competitions"]  # type: ignore

    stats = {
        "total_membres": total_membres,
        "cotisations_impayees": cotisations_impayees,
        "total_equipes": total_equipes,
        "prochaines_competitions": prochaines_competitions_count,
    }

    cursor.execute("""
            SELECT m.nom, m.prenom, c.montant, c.saison
            FROM Cotisation c
            JOIN Membre m ON c.membre_id = m.num_licence
            Where c.statut = 'impayee'
            ORDER BY saison DESC
        """)

    membres_impayees = cursor.fetchall()

    cursor.execute("""
            SELECT nom, date, lieu, type
            FROM Competition
            WHERE date >= CURDATE()
            ORDER BY date ASC
        """)

    prochaines_competitions = cursor.fetchall()

    cursor.execute("""
            SELECT m.nom, m.prenom, e.nom AS equipe,
            ROUND(COUNT(CASE WHEN p.present = 1 THEN 1 END) * 100.0 / COUNT(*)) AS taux
            FROM Presence p
            JOIN Membre m ON p.membre_id = m.num_licence
            JOIN Entrainement en ON p.entrainement_id = en.id
            JOIN Appartenance a ON a.membre_id = m.num_licence AND en.equipe_id = a.equipe_id AND a.date_sortie IS NULL
            JOIN Equipe e ON e.code = a.equipe_id
            GROUP BY m.num_licence, e.code
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
