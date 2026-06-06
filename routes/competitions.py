from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_db

competitions_bp = Blueprint("competitions", __name__, url_prefix="/competitions")


@competitions_bp.route("/", methods=["GET"])
def list_competitions():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = """
            SELECT c.nom, c.date, c.lieu, c.type, c.id AS id_competition, s.nom AS sport, (
                SELECT COUNT(*) FROM Participation p WHERE p.competition_id = c.id
            ) AS nb_participants
            FROM Competition c
            JOIN Sport s ON c.sport_id = s.id
            WHERE 1 = 1
        """

    params = []

    type_filtre = request.args.get("type")

    if type_filtre:
        query += " AND type = %s"
        params.append(type_filtre)

    query += " ORDER BY c.date DESC"

    cursor.execute(query, params)

    competitions = cursor.fetchall()
    cursor.close()

    return render_template("competitions/list.html", competitions=competitions)


@competitions_bp.route("/ajouter", methods=["GET", "POST"])
def add():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
                INSERT INTO Competition (nom, sport_id, date, lieu, type)
                VALUES (%s, %s, %s, %s, %s)
            """,
            (
                request.form["nom"],
                request.form["id_sport"],
                request.form["date"],
                request.form["lieu"],
                request.form["type"],
            ),
        )

        competition_id = cursor.lastrowid

        equipes = request.form.getlist("equipes")

        for equipe in equipes:
            if request.form["type"] in ("championnat", "coupe"):
                cursor.execute(
                    """
                        SELECT m.nom, m.prenom
                        FROM Membre m
                        JOIN Appartenir a ON a.Num_Licence = m.num_licence
                        JOIN Cotisation c ON c.num_licence = m.num_licence
                        WHERE a.equipe_id = %s AND a.date_sortie IS NULL
                        AND c.statut = 'impayee'
                    """,
                    (equipe,),
                )
                impayees = cursor.fetchall()

                if impayees:
                    noms = ", ".join(f"{m['prenom']} {m['nom']}" for m in impayees)  # type: ignore
                    flash(
                        f"Équipe {equipe} bloquée - cotisations impayées: {noms}",
                        "danger",
                    )
                    continue

            cursor.execute(
                """
                INSERT INTO Participation (equipe_id, competition_id)
                    VALUES (%s, %s)
                """,
                (
                    equipe,
                    competition_id,
                ),
            )

        db.commit()
        cursor.close()
        flash("Competition ajoutée avec succès", "success")

        return redirect(url_for("competitions.list_competitions"))

    cursor.execute("""
            SELECT s.nom, s.id AS id_sport
            FROM Sport s
        """)
    sports = cursor.fetchall()

    cursor.execute("""
            SELECT code AS code_equipe, nom
            FROM Equipe
        """)

    equipes = cursor.fetchall()

    cursor.close()

    return render_template("competitions/add.html", sports=sports, equipes=equipes)


@competitions_bp.route("/<int:id>/resultats", methods=["GET", "POST"])
def resultats(id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
            SELECT p.id, p.competition_id, p.equipe_id AS code_equipe, p.resultat, p.classement, e.nom AS equipe
            FROM Participation p
            JOIN Equipe e on p.equipe_id = e.code
            WHERE p.competition_id = %s
            ORDER BY p.classement ASC
        """,
        (id,),
    )

    participations = cursor.fetchall()

    if request.method == "POST":
        for p in participations:
            resultat = request.form.get(f"resultat_{p['code_equipe']}")  # type: ignore
            classement = request.form.get(f"classement_{p['code_equipe']}") or None  # type: ignore
            cursor.execute(
                """
                    UPDATE Participation
                    SET resultat = %s, classement = %s
                    WHERE competition_id = %s AND equipe_id = %s
                """,
                (
                    resultat,
                    classement,
                    id,
                    p["code_equipe"],  # type: ignore
                ),
            )

        db.commit()
        cursor.close()
        flash("Résultat enregistré avec succès", "success")

        return redirect(url_for("competitions.list_competitions"))

    cursor.execute(
        """
            SELECT c.nom, c.date, c.lieu, c.type, c.id AS id_competition
            FROM Competition c
            WHERE c.id = %s
        """,
        (id,),
    )

    competition = cursor.fetchone()

    cursor.close()

    return render_template(
        "competitions/resultats.html",
        participations=participations,
        competition=competition,
    )
