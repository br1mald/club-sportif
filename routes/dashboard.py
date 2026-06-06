from flask import Blueprint, flash, redirect, render_template, request, url_for

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/", methods=["GET"])
def index():
    return "TODO"
