from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from db import get_db

membres_bp = Blueprint("membres", __name__, url_prefix="/membres")


@membres_bp.route("/", methods=["GET"])
def list_membres():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
            SELECT m.*, e.nom AS equipe_nom
            FROM Membre m
            LEFT JOIN Appartenance a ON m.num_licence = a.membre_id AND a.date_sortie IS NULL
            LEFT JOIN Equipe e ON a.equipe_id = e.code
        """)
    # a.date_sortie IS NULL parce qu'on veut l'équipe actuelle, pas les équipes précédentes si il y en a
    # double join parce que le membre n'a pas directement accès à son équipe
    membres = cursor.fetchall()
    cursor.close()

    return render_template("membres/liste.html", membres=membres)


@membres_bp.route("/<int:id>", methods=["GET"])
def fiche(id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
            SELECT * FROM Membre WHERE num_licence = %s
        """,
        (id,),
    )
    membre = cursor.fetchone()

    if not membre:
        abort(404)

    cursor.execute(
        """
            SELECT COUNT (CASE WHEN p.presence = 1 THEN 1 END) * 100.0 /
            COUNT (*) AS taux
            FROM Presence p
            JOIN Entrainement en ON p.entrainement_id = en.id
            JOIN Appartenance a ON a.membre_id = p.membre_id
            AND a.equipe_id = en.equipe_id
            WHERE p.membre_id = %s
        """,
        (id,),
    )
    # CASE p.presence = 1 THEN 1 END ne comptabilise l'entrée que si le membre est présent (p.presence = 1)
    assiduite = cursor.fetchone()

    cursor.execute(
        "SELECT * FROM Cotisation c WHERE membre_id = %s ORDER BY saison DESC", (id,)
    )
    cotisations = cursor.fetchall()

    cursor.close()

    return render_template(
        "membres/fiche.html",
        membre=membre,
        assiduite=assiduite,
        cotisations=cotisations,
    )


@membres_bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
                INSERT INTO Membre (nom, prenom, date_naissance, telephone, email, date_inscription)
                VALUES (%s, %s, %s, %s, %s, CURDATE())
            """,
            (
                request.form["nom"],
                request.form["prenom"],
                request.form["date_naissance"],
                request.form["telephone"],
                request.form["email"],
            ),
        )
        db.commit()
        cursor.close()
        flash("Membre ajouté avec succès")
        return redirect(url_for("membres.list_membres"))

    return render_template("membres/add.html")


@membres_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
                UPDATE Membre SET
                nom = %s, prenom = %s, telephone = %s, email = %s
                WHERE num_licence = %s
            """,
            (
                request.form["nom"],
                request.form["prenom"],
                request.form["telephone"],
                request.form["email"],
                id,
            ),
        )

        db.commit()
        cursor.close()

        flash("Membre modifié avec succès")
        return redirect(url_for("membres.fiche", id=id))

    cursor.execute("SELECT * FROM Membre WHERE num_licence = %s", (id,))
    membre = cursor.fetchone()
    cursor.close()

    if not membre:
        abort(404)

    return render_template("membres/edit.html", membre=membre)


@membres_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM Membre WHERE num_licence = %s", (id,))
    db.commit()
    cursor.close()

    flash("Membre supprimé avec succès")
    return redirect("membres.list_membres")
