from flask import Blueprint, jsonify

api = Blueprint("api", __name__)

from . import roads  # noqa: E402  # imports needs to be after Blueprint init
from . import bollards  # noqa: E402
from . import permits  # noqa: E402
from . import isochrones  # noqa: E402
from . import road_elements  # noqa: E402
from . import road_obstructions  # noqa: E402
from .road_sections import load_unload  # noqa: E402
from . import traffic_signs  # noqa: E402


# Return validation errors as JSON
# https://webargs.readthedocs.io/en/latest/framework_support.html#error-handling
@api.errorhandler(422)
@api.errorhandler(400)
def handle_error(err):
    headers = err.data.get("headers", None)
    messages = err.data.get("messages", ["Invalid request."])

    if headers:
        return jsonify({"errors": messages}), err.code, headers
    else:
        return jsonify({"errors": messages}), err.code
