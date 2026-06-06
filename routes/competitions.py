from flask import Blueprint, flash, redirect, render_template, request, url_for

competitions_bp = Blueprint("competitions", __name__, url_prefix="/competitions")


@competitions_bp.route("/", methods=["GET"])
def list_competitions():
    return "TODO"
