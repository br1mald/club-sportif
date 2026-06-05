from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from db import get_db

membres_bp = Blueprint("membres", __name__, url_prefix="/membres")


@membres_bp.route("/", methods=["GET"])
def list_membres():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    recherche = request.args.get("recherche", "")
    equipe_filtre = request.args.get("equipe")

    query = """
            SELECT m.*, e.nom AS equipe
            FROM Membre m
            LEFT JOIN Appartenance a ON m.num_licence = a.membre_id AND a.date_sortie IS NULL
            LEFT JOIN Equipe e ON a.equipe_id = e.code
            WHERE 1 = 1
        """
    # a.date_sortie IS NULL parce qu'on veut l'équipe actuelle, pas les équipes précédentes si il y en a
    # double join parce que le membre n'a pas directement accès à son équipe

    params = []

    if recherche:
        query += " AND (m.nom LIKE %s OR m.prenom LIKE %s)"
        params.extend([f"%{recherche}%", f"%{recherche}%"])

    if equipe_filtre:
        query += " AND e.code = %s"
        params.append(equipe_filtre)

    cursor.execute(query, params)
    membres = cursor.fetchall()

    cursor.execute("SELECT code AS code_equipe, nom FROM Equipe")
    equipes = cursor.fetchall()

    cursor.close()

    return render_template(
        "membres/list.html",
        membres=membres,
        equipes=equipes,
        equipe_filtre=equipe_filtre,
        recherche=recherche,
    )


@membres_bp.route("/<int:id>", methods=["GET"])
def fiche(id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
            SELECT m.*, e.nom AS equipe FROM Membre m
            LEFT JOIN Appartenance a ON m.num_licence = a.membre_id AND a.date_sortie IS NULL
            LEFT JOIN Equipe e on a.equipe_id = e.code
            WHERE m.num_licence = %s
        """,
        (id,),
    )
    membre = cursor.fetchone()

    if not membre:
        abort(404)

    cursor.execute(
        """
            SELECT COUNT(CASE WHEN p.presence = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) AS taux
            FROM Presence p
            JOIN Entrainement en ON p.entrainement_id = en.id
            JOIN Appartenance a ON a.membre_id = p.membre_id
            AND a.equipe_id = en.equipe_id
            WHERE p.membre_id = %s
        """,
        (id,),
    )
    # CASE p.presence = 1 THEN 1 END ne comptabilise l'entrée que si le membre est présent (p.presence = 1)
    assiduite: dict | None = cursor.fetchone()  # type: ignore
    taux_assiduite = int(assiduite["taux"]) if assiduite and assiduite["taux"] else 0

    cursor.execute(
        "SELECT * FROM Cotisation c WHERE membre_id = %s ORDER BY saison DESC", (id,)
    )
    cotisations = cursor.fetchall()

    cursor.execute(
        """
            SELECT en.date, en.theme, p.presence, p.motif_absence
            FROM Presence p
            JOIN Entrainement en ON p.entrainement_id = en.id
            WHERE p.membre_id = %s
            ORDER BY en.date DESC
        """,
        (id,),
    )
    presences = cursor.fetchall()

    cursor.close()

    return render_template(
        "membres/fiche.html",
        membre=membre,
        taux_assiduite=taux_assiduite,
        cotisations=cotisations,
        presences=presences,
    )


@membres_bp.route("/ajouter", methods=["GET", "POST"])
def add():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
                INSERT INTO Membre (nom, prenom, date_naissance, telephone, email, date_adhesion)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                request.form["nom"],
                request.form["prenom"],
                request.form["date_naissance"],
                request.form["telephone"],
                request.form["email"],
                request.form["date_adhesion"],
            ),
        )

        if request.form.get("code_equipe"):
            cursor.execute(
                """
                    INSERT INTO Appartenance (membre_id, equipe_id, date_adhesion)
                    VALUES (%s, %s, CURDATE())
                """,
                (cursor.lastrowid, request.form["code_equipe"]),
            )

        db.commit()
        cursor.close()
        flash("Membre ajouté avec succès", "success")
        return redirect(url_for("membres.list_membres"))

    cursor.execute("""
            SELECT e.nom, e.categorie, e.code AS code_equipe FROM Equipe e
        """)
    equipes = cursor.fetchall()

    cursor.close()

    return render_template("membres/add.html", equipes=equipes)


@membres_bp.route("/<int:id>/modifier", methods=["GET", "POST"])
def edit(id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
                UPDATE Membre SET
                nom = %s, prenom = %s, telephone = %s, email = %s, date_naissance = %s, date_adhesion = %s
                WHERE num_licence = %s
            """,
            (
                request.form["nom"],
                request.form["prenom"],
                request.form["telephone"],
                request.form["email"],
                request.form["date_naissance"],
                request.form["date_adhesion"],
                id,
            ),
        )

        cursor.execute(
            """
                SELECT a.equipe_id FROM Appartenance a
                WHERE a.membre_id = %s and a.date_sortie IS NULL
            """,
            (id,),
        )

        current_team = cursor.fetchone()
        if request.form.get("code_equipe"):
            if not current_team:
                cursor.execute(
                    "INSERT INTO Appartenance (membre_id, equipe_id, date_adhesion) VALUES (%s, %s, CURDATE())",
                    (id, request.form["code_equipe"]),
                )

            elif str(current_team["equipe_id"]) != request.form["code_equipe"]:  # type: ignore
                cursor.execute(
                    """
                        UPDATE Appartenance SET date_sortie = CURDATE()
                        WHERE membre_id = %s AND date_sortie IS NULL
                    """,
                    (id,),
                )

                cursor.execute(
                    """
                        INSERT INTO Appartenance(membre_id, equipe_id, date_adhesion)
                        VALUES (%s, %s, CURDATE())
                    """,
                    (id, request.form["code_equipe"]),
                )
        else:
            cursor.execute(
                """
                    UPDATE Appartenance SET
                    date_sortie = CURDATE()
                    WHERE membre_id = %s AND date_sortie IS NULL
                """,
                (id,),
            )

        db.commit()
        cursor.close()

        flash("Membre modifié avec succès", "success")
        return redirect(url_for("membres.fiche", id=id))

    cursor.execute(
        """SELECT m.*, a.equipe_id AS code_equipe
        FROM Membre m
        LEFT JOIN Appartenance a ON m.num_licence = a.membre_id AND a.date_sortie IS NULL
        WHERE m.num_licence = %s""",
        (id,),
    )
    membre = cursor.fetchone()

    if not membre:
        abort(404)

    cursor.execute("""
            SELECT e.nom, e.code AS code_equipe, e.categorie FROM Equipe e
        """)

    equipes = cursor.fetchall()

    cursor.close()
    return render_template("membres/modifier.html", membre=membre, equipes=equipes)


@membres_bp.route("/<int:id>/supprimer", methods=["POST"])
def delete(id: int):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM Membre WHERE num_licence = %s", (id,))
    db.commit()
    cursor.close()

    flash("Membre supprimé avec succès", "success")
    return redirect(url_for("membres.list_membres"))
