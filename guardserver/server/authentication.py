from . import app
import ldap
from flask import request, Response
from functools import wraps
import re


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    valid = re.match("^[\w.]+$", username) is not None
    if not valid:
        return False
    user_dn = app.config["LDAP_DN"] % username
    connect = ldap.initialize(app.config["LDAP_SERVER"])
    try:
        connect.bind_s(user_dn, password)
        return True
    except ldap.LDAPError, e:
        connect.unbind_s()
        return False


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated

