from datetime import date, datetime

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
            SELECT m.*, e.Nom_Equipe AS equipe
            FROM Membre m
            LEFT JOIN Appartenir a ON m.Num_Licence = a.Num_Licence AND a.Date_Sortie IS NULL
            LEFT JOIN Equipe e ON a.Code_Equipe = e.Code_Equipe
            WHERE 1 = 1
        """

    params = []

    if recherche:
        query += " AND (m.Nom LIKE %s OR m.Prenom LIKE %s)"
        params.extend([f"%{recherche}%", f"%{recherche}%"])

    if equipe_filtre:
        query += " AND e.Code_Equipe = %s"
        params.append(equipe_filtre)

    cursor.execute(query, params)
    membres = cursor.fetchall()

    cursor.execute("SELECT Code_Equipe AS code_equipe, Nom_Equipe FROM Equipe")
    equipes = cursor.fetchall()

    cursor.close()

    return render_template(
        "membres/list.html",
        membres=membres,
        equipes=equipes,
        equipe_filtre=equipe_filtre,
        recherche=recherche,
    )


@membres_bp.route("/<id>", methods=["GET"])
def fiche(id: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
            SELECT m.*, e.Nom_Equipe AS equipe FROM Membre m
            LEFT JOIN Appartenir a ON m.Num_Licence = a.Num_Licence AND a.Date_Sortie IS NULL
            LEFT JOIN Equipe e ON a.Code_Equipe = e.Code_Equipe
            WHERE m.Num_Licence = %s
        """,
        (id,),
    )
    membre = cursor.fetchone()

    if not membre:
        abort(404)

    cursor.execute(
        """
            SELECT COUNT(CASE WHEN p.Present = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) AS taux
            FROM Presence p
            JOIN Entrainement en ON p.Entrain_ID = en.Entrain_ID
            JOIN Appartenir a ON a. Num_Licence = p.Num_Licence
            AND a.Code_Equipe = en.Code_Equipe
            WHERE p.Num_Licence = %s
        """,
        (id,),
    )
    assiduite = cursor.fetchone()
    taux_assiduite = int(assiduite["taux"]) if assiduite and assiduite["taux"] else 0  # type: ignore

    cursor.execute(
        "SELECT * FROM Cotisation WHERE Num_Licence = %s ORDER BY Saison DESC", (id,)
    )
    cotisations = cursor.fetchall()

    cursor.execute(
        """
            SELECT en.Date, en.Theme, p.Present, p.Motif_Absence
            FROM Presence p
            JOIN Entrainement en ON p.Entrain_ID = en.Entrain_ID
            WHERE p.Num_Licence = %s
            ORDER BY en.Date DESC
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
        cursor.execute("SELECT MAX(Num_Licence) AS max_lic FROM Membre")
        result = cursor.fetchone()
        if result and result["max_lic"]:  # type: ignore
            next_num = int(result["max_lic"][3:]) + 1  # type: ignore
        else:
            next_num = 1
        num_licence = f"LIC{next_num:05d}"

        cursor.execute(
            """
                INSERT INTO Membre (Num_Licence, Nom, Prenom, Date_Naissance, Telephone, Email, Date_Adhesion)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                num_licence,
                request.form["nom"],
                request.form["prenom"],
                request.form["date_naissance"],
                request.form["telephone"],
                request.form["email"],
                request.form["date_adhesion"],
            ),
        )

        code_equipe = request.form.get("code_equipe")
        if code_equipe:
            cursor.execute(
                "SELECT Categorie FROM Equipe WHERE Code_Equipe = %s", (code_equipe,)
            )
            equipe = cursor.fetchone()

            date_of_birth = datetime.strptime(
                request.form["date_naissance"], "%Y-%m-%d"
            ).date()

            age = (date.today() - date_of_birth).days // 365

            if equipe["Categorie"] == "senior" and age < 16:  # type: ignore
                db.rollback()
                flash(
                    "Le membre doit avoir au moins 16 ans pour rejoindre une équipe senior",
                    "danger",
                )
                return redirect(request.url)

            cursor.execute(
                """
                    SELECT e.Nom_Equipe
                    FROM Appartenir a
                    JOIN Equipe e ON e.Code_Equipe = a.Code_Equipe
                    WHERE a.Num_Licence = %s AND a.Date_Sortie IS NULL
                    AND e.Sport_ID = (SELECT Sport_ID FROM Equipe WHERE Code_Equipe = %s)
                """,
                (num_licence, code_equipe),
            )

            existing = cursor.fetchone()
            if existing:
                db.rollback()
                flash(
                    f"Ce membre appartient déjà à {existing['Nom_Equipe']} dans ce sport",  # type: ignore
                    "danger",
                )
                return redirect(request.url)

            cursor.execute(
                """
                    INSERT INTO Appartenir (Num_Licence, Code_Equipe, Date_Entree, Poste)
                    VALUES (%s, %s, CURDATE(), %s)
                """,
                (num_licence, code_equipe, request.form.get("poste", "Non défini")),
            )

        db.commit()
        cursor.close()
        flash("Membre ajouté avec succès", "success")
        return redirect(url_for("membres.list_membres"))

    cursor.execute("""
            SELECT Nom_Equipe, Categorie, Code_Equipe AS code_equipe FROM Equipe
        """)
    equipes = cursor.fetchall()

    cursor.close()

    return render_template("membres/add.html", equipes=equipes)


@membres_bp.route("/<id>/modifier", methods=["GET", "POST"])
def edit(id: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
                UPDATE Membre SET
                Nom = %s, Prenom = %s, Telephone = %s, Email = %s, Date_Naissance = %s, Date_Adhesion = %s
                WHERE Num_Licence = %s
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
                SELECT a.Code_Equipe FROM Appartenir a
                WHERE a.Num_Licence = %s AND a.Date_Sortie IS NULL
            """,
            (id,),
        )

        current_team = cursor.fetchone()
        code_equipe = request.form.get("code_equipe")
        if code_equipe:
            cursor.execute(
                "SELECT Categorie FROM Equipe WHERE Code_Equipe = %s", (code_equipe,)
            )
            equipe = cursor.fetchone()

            date_of_birth = datetime.strptime(
                request.form["date_naissance"], "%Y-%m-%d"
            ).date()

            age = (date.today() - date_of_birth).days // 365

            if equipe["Categorie"] == "senior" and age < 16:  # type: ignore
                db.rollback()
                flash(
                    "Le membre doit avoir au moins 16 ans pour rejoindre une équipe senior",
                    "danger",
                )
                return redirect(request.url)

            cursor.execute(
                """
                    SELECT e.Nom_Equipe
                    FROM Appartenir a
                    JOIN Equipe e ON e.Code_Equipe = a.Code_Equipe
                    WHERE a.Num_Licence = %s AND a.Date_Sortie IS NULL
                    AND e.Sport_ID = (SELECT Sport_ID FROM Equipe WHERE Code_Equipe = %s)
                """,
                (id, code_equipe),
            )

            existing = cursor.fetchone()
            if existing:
                db.rollback()
                flash(
                    f"Ce membre appartient déjà à {existing['Nom_Equipe']} dans ce sport",  # type: ignore
                    "danger",
                )
                return redirect(request.url)

            if not current_team:
                cursor.execute(
                    "INSERT INTO Appartenir (Num_Licence, Code_Equipe, Date_Entree, Poste) VALUES (%s, %s, CURDATE(), %s)",
                    (id, code_equipe, request.form.get("poste", "Non défini")),
                )

            elif current_team["Code_Equipe"] != code_equipe:  # type: ignore
                cursor.execute(
                    """
                        UPDATE Appartenir SET Date_Sortie = CURDATE()
                        WHERE Num_Licence = %s AND Date_Sortie IS NULL
                    """,
                    (id,),
                )

                cursor.execute(
                    """
                        INSERT INTO Appartenir (Num_Licence, Code_Equipe, Date_Entree, Poste)
                        VALUES (%s, %s, CURDATE(), %s)
                    """,
                    (id, code_equipe, request.form.get("poste", "Non défini")),
                )
        else:
            cursor.execute(
                """
                    UPDATE Appartenir SET Date_Sortie = CURDATE()
                    WHERE Num_Licence = %s AND Date_Sortie IS NULL
                """,
                (id,),
            )

        db.commit()
        cursor.close()

        flash("Membre modifié avec succès", "success")
        return redirect(url_for("membres.fiche", id=id))

    cursor.execute(
        """SELECT m.*, a.Code_Equipe AS code_equipe
        FROM Membre m
        LEFT JOIN Appartenir a ON m.Num_Licence = a.Num_Licence AND a.Date_Sortie IS NULL
        WHERE m.Num_Licence = %s""",
        (id,),
    )
    membre = cursor.fetchone()

    if not membre:
        abort(404)

    cursor.execute("""
            SELECT Nom_Equipe, Code_Equipe AS code_equipe, Categorie FROM Equipe
        """)

    equipes = cursor.fetchall()

    cursor.close()
    return render_template("membres/modifier.html", membre=membre, equipes=equipes)


@membres_bp.route("/<id>/supprimer", methods=["POST"])
def delete(id: str):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM Membre WHERE Num_Licence = %s", (id,))
    db.commit()
    cursor.close()

    flash("Membre supprimé avec succès", "success")
    return redirect(url_for("membres.list_membres"))
