from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_db

entrainements_bp = Blueprint("entrainements", __name__, url_prefix="/entrainements")


@entrainements_bp.route("/", methods=["GET"])
def list_entrainements():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = """
            SELECT en.*, e.nom AS equipe
            FROM Entrainement en
            JOIN Equipe e ON en.equipe_id = e.code
            WHERE 1 = 1
        """

    params = []

    equipe_filtre = request.args.get("equipe")

    if equipe_filtre:
        query += " AND e.code = %s"
        params.append(equipe_filtre)

    cursor.execute(query, params)

    entrainements = cursor.fetchall()

    cursor.execute("SELECT nom, code AS code_equipe, categorie FROM Equipe")
    equipes = cursor.fetchall()

    cursor.close()

    return render_template(
        "entrainements/list.html", entrainements=entrainements, equipes=equipes
    )


@entrainements_bp.route("/ajouter", methods=["GET", "POST"])
def add():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
                INSERT INTO Entrainement (date, heure_debut, duree, lieu, theme, equipe_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                request.form["date"],
                request.form["heure_debut"],
                request.form["duree"],
                request.form["lieu"],
                request.form["theme"],
                request.form["code_equipe"],
            ),
        )

        db.commit()
        cursor.close()
        flash("Entraînement enregistré avec succès", "success")

        return redirect(url_for("entrainements.list_entrainements"))

    cursor.execute("""
            SELECT e.nom, e.categorie, e.code AS code_equipe
            FROM Equipe e
        """)

    equipes = cursor.fetchall()
    cursor.close()

    return render_template("entrainements/add.html", equipes=equipes)


@entrainements_bp.route("/<id>/presences", methods=["GET", "POST"])
def presence(id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
                SELECT a.membre_id FROM Appartenance a
                WHERE equipe_id = (SELECT equipe_id FROM Entrainement WHERE id = %s)
                AND date_sortie IS NULL
            """,
            (id,),
        )

        membres = cursor.fetchall()

        for m in membres:
            present = 1 if request.form.get(f"present_{m['membre_id']}") else 0  # type: ignore
            motif = request.form.get(f"motif_{m['membre_id']}")  # type: ignore
            cursor.execute(
                """
                    INSERT INTO Presence (membre_id, entrainement_id, present, motif_absence)
                    VALUES (%s, %s, %s, %s)
                """,
                (
                    m["membre_id"],  # type: ignore
                    id,
                    present,
                    motif,
                ),
            )  # type: ignore
        cursor.close()
        db.commit()
        flash("Presences enregistrées avec succès", "success")
        return redirect(url_for("entrainements.list_entrainements"))

    cursor.execute(
        """
            SELECT en.date, en.theme, en.lieu, e.nom AS equipe
            FROM Entrainement en
            JOIN Equipe e ON en.equipe_id = e.code
            WHERE en.id = %s
        """,
        (id,),
    )

    entrainement = cursor.fetchone()

    cursor.execute(
        """
            SELECT COUNT(*) AS presents FROM Presence
            WHERE present = 1 AND entrainement_id = %s
        """,
        (id,),
    )

    nb_presents = cursor.fetchone()["presents"]  # type: ignore

    cursor.execute(
        """
            SELECT COUNT(*) AS total FROM Appartenance a
            WHERE a.equipe_id = (SELECT en.equipe_id FROM Entrainement en WHERE id = %s)
            AND date_sortie IS NULL
        """,
        (id,),
    )

    total_membres = cursor.fetchone()["total"]  # type: ignore

    taux = (nb_presents / total_membres) * 100 if total_membres > 0 else 0  # type: ignore

    cursor.execute(
        """
            SELECT m.nom, m.prenom, m.num_licence, p.present, p.motif_absence
            FROM Membre m
            JOIN Appartenance a ON a.membre_id = m.num_licence
            LEFT JOIN Presence p ON p.membre_id = m.num_licence AND p.entrainement_id = %s
            WHERE a.equipe_id = (SELECT equipe_id FROM Entrainement en WHERE en.id = %s)
            AND a.date_sortie IS NULL
        """,
        (
            id,
            id,
        ),
    )

    membres = cursor.fetchall()

    cursor.close()

    return render_template(
        "entrainements/presence.html",
        entrainement=entrainement,
        nb_presents=nb_presents,
        total_membres=total_membres,
        taux=taux,
        membres=membres,
    )
