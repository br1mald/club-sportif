from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_db

cotisations_bp = Blueprint("cotisations", __name__, url_prefix="/cotisations")


@cotisations_bp.route("/", methods=["GET"])
def list_cotisations():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    statut_filtre = request.args.get("statut")
    saison_filtre = request.args.get("saison")

    query = """
        SELECT m.Nom, m.Prenom, c.Saison, c.Montant, c.Date_Paiement, c.Statut, c.Cotis_ID AS id_cotisation
        FROM Cotisation c
        JOIN Membre m ON c.Num_Licence = m.Num_Licence
        WHERE 1 = 1
    """

    params = []

    if statut_filtre:
        query += " AND c.Statut = %s"
        params.append(statut_filtre)
    if saison_filtre:
        query += " AND c.Saison = %s"
        params.append(saison_filtre)

    cursor.execute(query, params)

    cotisations = cursor.fetchall()

    cursor.execute("""
            SELECT DISTINCT Saison
            FROM Cotisation ORDER BY Saison DESC
        """)

    saisons = [row["Saison"] for row in cursor.fetchall()]  # type: ignore

    cursor.execute("""
            SELECT COUNT(*) AS total
            FROM Cotisation WHERE Statut = 'impayee'
        """)

    nb_impayees = cursor.fetchone()["total"]  # type: ignore

    return render_template(
        "cotisations/list.html",
        cotisations=cotisations,
        saisons=saisons,
        nb_impayees=nb_impayees,
    )


@cotisations_bp.route("/<int:id>/payer", methods=["GET", "POST"])
def payer(id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
                UPDATE Cotisation
                SET Statut = 'payee', Date_Paiement = %s, Montant = %s
                WHERE Cotis_ID = %s
            """,
            (
                request.form["date_paiement"],
                request.form["montant"],
                id,
            ),
        )

        db.commit()
        cursor.close()
        flash("Cotisation payée avec succès", "success")

        return redirect(url_for("cotisations.list_cotisations"))

    cursor.execute(
        """
            SELECT m.Prenom, m.Nom, c.Saison, c.Montant, c.Cotis_ID AS id_cotisation
            FROM Cotisation c
            JOIN Membre m ON c.Num_Licence = m.Num_Licence
            WHERE c.Cotis_ID = %s
        """,
        (id,),
    )

    cotisation = cursor.fetchone()

    cursor.close()

    return render_template("cotisations/payer.html", cotisation=cotisation)
