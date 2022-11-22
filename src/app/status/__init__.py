from flask import Blueprint

status = Blueprint("status", __name__)

from . import health  # noqa: E402  # imports needs to be after Blueprint init
