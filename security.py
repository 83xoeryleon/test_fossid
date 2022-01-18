from flask import abort
from flask_security import Security, SQLAlchemyUserDatastore
from flask_security.utils import verify_hash

from ... import security
from ...db import sa


def _request_loader(request):
    # This function is copied from `flask-security/core.py:_request_loader`.
    header_key = security.token_authentication_header
    token = request.headers.get(header_key, None)
    from_dtool = request.headers.get('Dtool') == 'true'
    try:
        data = security.remember_token_serializer.loads(
            token, max_age=security.token_max_age)
        user = security.datastore.find_user(id=data[0])
        if user:
            # Because password can be anything when request from mini-mall,
            # `verify_hash` is no longer called.
            if not from_dtool or \
                    (from_dtool and verify_hash(data[1], user.password)):
                return user
    except:
        pass
    return security.login_manager.anonymous_user()


def install(app):
    from .models import User, Role
    Security(app, datastore=SQLAlchemyUserDatastore(sa, User, Role),
             register_blueprint=False)
    security = app.extensions['security']
    security.login_manager.unauthorized_handler(lambda: abort(401))
    security.login_manager.request_loader(_request_loader)
    security.unauthorized_handler(lambda: abort(401))
