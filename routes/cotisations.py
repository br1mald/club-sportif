from flask import Blueprint, flash, redirect, render_template, request, url_for

cotisations_bp = Blueprint("cotisations", __name__, url_prefix="/cotisations")


@cotisations_bp.route("/", methods=["GET"])
def list_cotisations():
    return "TODO"
