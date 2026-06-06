from types import coroutine

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
        SELECT m.nom, m.prenom, c.saison, c.montant, c.date_paiement, c.statut, c.id_cotisation
        FROM Cotisation c
        JOIN Membre m ON c.membre_id = m.num_licence
        WHERE 1 = 1
    """

    params = []

    if statut_filtre:
        query += " AND statut = %s"
        params.append(statut_filtre)
    if saison_filtre:
        query += " AND saison = %s"
        params.append(saison_filtre)

    cursor.execute(query, params)

    cotisations = cursor.fetchall()

    cursor.execute("""
            SELECT DISTINCT saison
            FROM Cotisation ORDER BY saison DESC
        """)

    saisons = [row["saison"] for row in cursor.fetchall()]  # type: ignore

    cursor.execute("""
            SELECT COUNT(*) AS total
            FROM Cotisation WHERE statut = 'impayee'
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
                SET statut = 'payee', date_paiement = %s, montant = %s
                WHERE id_cotisation = %s
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
            SELECT m.prenom, m.nom, c.saison, c.montant, c.id_cotisation
            FROM Cotisation c
            JOIN Membre m ON c.membre_id = m.num_licence
            WHERE c.id_cotisation = %s
        """,
        (id,),
    )

    cotisation = cursor.fetchone()

    cursor.close()

    return render_template("cotisations/payer.html", cotisation=cotisation)
