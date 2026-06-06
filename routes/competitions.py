from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_db

competitions_bp = Blueprint("competitions", __name__, url_prefix="/competitions")


@competitions_bp.route("/", methods=["GET"])
def list_competitions():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = """
            SELECT c.Nom, c.Date, c.Lieu, c.Type, c.Comp_ID AS id_competition, s.Nom AS sport, (
                SELECT COUNT(*) FROM Participation p WHERE p.Comp_ID = c.Comp_ID
            ) AS nb_participants
            FROM Competition c
            JOIN Sport s ON c.Sport_ID = s.Sport_ID
            WHERE 1 = 1
        """

    params = []

    type_filtre = request.args.get("type")

    if type_filtre:
        query += " AND c.Type = %s"
        params.append(type_filtre)

    query += " ORDER BY c.Date DESC"

    cursor.execute(query, params)

    competitions = cursor.fetchall()
    cursor.close()

    return render_template("competitions/list.html", competitions=competitions)


@competitions_bp.route("/ajouter", methods=["GET", "POST"])
def add():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute("SELECT MAX(Comp_ID) AS max_id FROM Competition")
        result = cursor.fetchone()
        if result and result["max_id"]:  # type: ignore
            next_num = int(result["max_id"][3:]) + 1  # type: ignore
        else:
            next_num = 1
        comp_id = f"CMP{next_num:04d}"

        cursor.execute(
            """
                INSERT INTO Competition (Comp_ID, Nom, Sport_ID, Date, Lieu, Type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                comp_id,
                request.form["nom"],
                request.form["id_sport"],
                request.form["date"],
                request.form["lieu"],
                request.form["type"],
            ),
        )

        equipes = request.form.getlist("equipes")
        print(equipes)

        for equipe in equipes:
            if request.form["type"] in ("championnat", "coupe"):
                cursor.execute(
                    """
                        SELECT m.Nom, m.Prenom
                        FROM Membre m
                        JOIN Appartenir a ON a.Num_Licence = m.Num_Licence
                        JOIN Cotisation c ON c.Num_Licence = m.Num_Licence
                        WHERE a.Code_Equipe = %s AND a.Date_Sortie IS NULL
                        AND c.Statut = 'impayee'
                    """,
                    (equipe,),
                )
                impayees = cursor.fetchall()

                if impayees:
                    noms = ", ".join(f"{m['Prenom']} {m['Nom']}" for m in impayees)  # type: ignore
                    flash(
                        f"Équipe {equipe} bloquée - cotisations impayées: {noms}",
                        "danger",
                    )
                    continue

            cursor.execute(
                """
                    INSERT INTO Participation (Code_Equipe, Comp_ID)
                    VALUES (%s, %s)
                """,
                (equipe, comp_id),
            )

        db.commit()
        cursor.close()
        flash("Compétition ajoutée avec succès", "success")

        return redirect(url_for("competitions.list_competitions"))

    cursor.execute("""
            SELECT s.Nom, s.Sport_ID AS id_sport
            FROM Sport s
        """)
    sports = cursor.fetchall()

    cursor.execute("""
            SELECT Code_Equipe AS code_equipe, Nom_Equipe
            FROM Equipe
        """)

    equipes = cursor.fetchall()

    cursor.close()

    return render_template("competitions/add.html", sports=sports, equipes=equipes)


@competitions_bp.route("/<id>/resultats", methods=["GET", "POST"])
def resultats(id: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
            SELECT p.Code_Equipe AS code_equipe, p.Resultat, e.Nom_Equipe AS equipe
            FROM Participation p
            JOIN Equipe e ON p.Code_Equipe = e.Code_Equipe
            WHERE p.Comp_ID = %s
        """,
        (id,),
    )

    participations = cursor.fetchall()

    if request.method == "POST":
        for p in participations:
            resultat = request.form.get(f"resultat_{p['code_equipe']}")  # type: ignore
            cursor.execute(
                """
                    UPDATE Participation
                    SET Resultat = %s
                    WHERE Comp_ID = %s AND Code_Equipe = %s
                """,
                (
                    resultat,
                    id,
                    p["code_equipe"],  # type: ignore
                ),
            )

        db.commit()
        cursor.close()
        flash("Résultats enregistrés avec succès", "success")

        return redirect(url_for("competitions.list_competitions"))

    cursor.execute(
        """
            SELECT c.Nom, c.Date, c.Lieu, c.Type, c.Comp_ID AS id_competition
            FROM Competition c
            WHERE c.Comp_ID = %s
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
