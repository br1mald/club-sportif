from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_db

entrainements_bp = Blueprint("entrainements", __name__, url_prefix="/entrainements")


@entrainements_bp.route("/", methods=["GET"])
def list_entrainements():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = """
            SELECT en.*, e.Nom_Equipe AS equipe
            FROM Entrainement en
            JOIN Equipe e ON en.Code_Equipe = e.Code_Equipe
            WHERE 1 = 1
        """

    params = []

    equipe_filtre = request.args.get("equipe")

    if equipe_filtre:
        query += " AND e.Code_Equipe = %s"
        params.append(equipe_filtre)

    cursor.execute(query, params)

    entrainements = cursor.fetchall()

    cursor.execute(
        "SELECT Nom_Equipe, Code_Equipe AS code_equipe, Categorie FROM Equipe"
    )
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
        cursor.execute("SELECT MAX(Entrain_ID) AS max_id FROM Entrainement")
        result = cursor.fetchone()
        if result and result["max_id"]:  # type: ignore
            next_num = int(result["max_id"][2:]) + 1  # type: ignore
        else:
            next_num = 1
        entrain_id = f"EN{next_num:06d}"

        cursor.execute(
            """
                INSERT INTO Entrainement (Entrain_ID, Date, Heure_Debut, Duree, Lieu, Theme, Code_Equipe)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                entrain_id,
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
            SELECT Nom_Equipe, Categorie, Code_Equipe AS code_equipe
            FROM Equipe
        """)

    equipes = cursor.fetchall()
    cursor.close()

    return render_template("entrainements/add.html", equipes=equipes)


@entrainements_bp.route("/<id>/presences", methods=["GET", "POST"])
def presence(id: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
                SELECT a.Num_Licence FROM Appartenir a
                WHERE Code_Equipe = (SELECT Code_Equipe FROM Entrainement WHERE Entrain_ID = %s)
                AND Date_Sortie IS NULL
            """,
            (id,),
        )

        membres = cursor.fetchall()

        for m in membres:
            present = 1 if request.form.get(f"present_{m['Num_Licence']}") else 0  # type: ignore
            motif = request.form.get(f"motif_{m['Num_Licence']}")  # type: ignore
            cursor.execute(
                """
                    INSERT INTO Presence (Num_Licence, Entrain_ID, Present, Motif_Absence)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE Present = VALUES(Present), Motif_Absence = VALUES(Motif_Absence)
                """,
                (
                    m["Num_Licence"],  # type: ignore
                    id,
                    present,
                    motif,
                ),
            )
        db.commit()
        cursor.close()
        flash("Présences enregistrées avec succès", "success")
        return redirect(url_for("entrainements.list_entrainements"))

    cursor.execute(
        """
            SELECT en. Entrain_ID, en.Date, en.Theme, en.Lieu, e.Nom_Equipe AS equipe
            FROM Entrainement en
            JOIN Equipe e ON en.Code_Equipe = e.Code_Equipe
            WHERE en.Entrain_ID = %s
        """,
        (id,),
    )

    entrainement = cursor.fetchone()

    cursor.execute(
        """
            SELECT COUNT(*) AS presents FROM Presence
            WHERE Present = 1 AND Entrain_ID = %s
        """,
        (id,),
    )

    nb_presents = cursor.fetchone()["presents"]  # type: ignore

    cursor.execute(
        """
            SELECT COUNT(*) AS total FROM Appartenir a
            WHERE a.Code_Equipe = (SELECT en.Code_Equipe FROM Entrainement en WHERE Entrain_ID = %s)
            AND Date_Sortie IS NULL
        """,
        (id,),
    )

    total_membres = cursor.fetchone()["total"]  # type: ignore

    taux = (nb_presents / total_membres) * 100 if total_membres > 0 else 0  # type: ignore

    cursor.execute(
        """
            SELECT m.Nom, m.Prenom, m.Num_Licence, p.Present, p.Motif_Absence
            FROM Membre m
            JOIN Appartenir a ON a.Num_Licence = m.Num_Licence
            LEFT JOIN Presence p ON p.Num_Licence = m.Num_Licence AND p.Entrain_ID = %s
            WHERE a.Code_Equipe = (SELECT Code_Equipe FROM Entrainement en WHERE en.Entrain_ID = %s)
            AND a.Date_Sortie IS NULL
        """,
        (id, id),
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
