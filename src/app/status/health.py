from flask import make_response

from . import status


@status.route("health")
def health_check():
    return make_response({"status": "OK", "content": "OK"}, 200)
