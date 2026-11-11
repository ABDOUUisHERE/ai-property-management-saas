"""HTTP identity entry point shared by authenticated modules."""

from fastapi import Request
from pydantic import SecretStr

from app.modules.identity.repository import Profile
from app.modules.identity.sessions import SessionService


def authenticated_profile(request: Request) -> Profile:
    service: SessionService = request.app.state.auth_sessions
    cookie = request.app.state.auth_security.session_cookie
    return service.resolve(SecretStr(request.cookies.get(cookie, "")))
