from typing import Any
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, FastAPI, Request, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.core.contracts import Problem
from app.core.errors import problem_response
from app.modules.identity.contracts import (
    AuthenticationRejected,
    ProviderThrottled,
    ProviderUnavailable,
)
from app.modules.identity.sessions import SessionBusy, SessionExpired, SessionService


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: str = Field(min_length=3, max_length=320, json_schema_extra={"format": "email"})
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_syntax(cls, value: str) -> str:
        try:
            # The demo deliberately uses reserved .test recipients and Mailpit.
            # Credential verification remains the provider's responsibility.
            return validate_email(
                value, check_deliverability=False, test_environment=value.lower().endswith(".test")
            ).normalized
        except EmailNotValidError:
            raise ValueError("Invalid email") from None


class Registration(Credentials):
    password: SecretStr = Field(min_length=12, max_length=128)


class ProfileResponse(BaseModel):
    id: UUID
    email: str


class SessionResponse(BaseModel):
    profile: ProfileResponse
    expires_at: AwareDatetime


class CsrfResponse(BaseModel):
    csrf_token: str


class RegistrationAccepted(BaseModel):
    status: str = "accepted"


def identity_router() -> APIRouter:
    problems: dict[int | str, dict[str, Any]] = {
        code: {"model": Problem, "content": {"application/problem+json": {}}}
        for code in (401, 403, 409, 413, 422, 429, 500, 503)
    }
    router = APIRouter(prefix="/api/v1", tags=["identity"], responses=problems)

    @router.get("/auth/csrf", response_model=CsrfResponse)
    def csrf(request: Request, response: Response) -> CsrfResponse:
        return CsrfResponse(csrf_token=request.app.state.auth_security.issue(request, response))

    @router.post("/auth/register", status_code=202, response_model=RegistrationAccepted)
    def register(body: Registration, request: Request) -> RegistrationAccepted:
        request.app.state.auth_limiter.check("register-email", str(body.email).lower(), 5, 3600)
        try:
            request.app.state.auth_provider.register(str(body.email), body.password)
        except (AuthenticationRejected, ProviderThrottled):
            pass  # An account's existence and upstream rejection details are not public.
        return RegistrationAccepted()

    @router.post("/auth/login", response_model=SessionResponse)
    def login(body: Credentials, request: Request, response: Response) -> SessionResponse:
        request.app.state.auth_limiter.check("login-email", str(body.email).lower(), 10, 60)
        service: SessionService = request.app.state.auth_sessions
        security = request.app.state.auth_security
        session = service.login(str(body.email), body.password)
        old = request.cookies.get(security.session_cookie)
        if old:
            service.logout(SecretStr(old))
        security.cookie(
            response,
            security.session_cookie,
            session.opaque.get_secret_value(),
            max(1, int((session.expires_at - request.app.state.clock.now()).total_seconds())),
        )
        security.clear(response, security.context_cookie)
        return SessionResponse(
            profile=ProfileResponse(id=session.profile.id, email=session.profile.email),
            expires_at=session.expires_at,
        )

    @router.get("/me", response_model=ProfileResponse)
    def me(request: Request) -> ProfileResponse:
        profile = request.app.state.auth_sessions.resolve(_opaque(request))
        return ProfileResponse(id=profile.id, email=profile.email)

    @router.post("/auth/refresh", response_model=ProfileResponse)
    def refresh(request: Request) -> ProfileResponse:
        profile = request.app.state.auth_sessions.resolve(_opaque(request), force_refresh=True)
        return ProfileResponse(id=profile.id, email=profile.email)

    @router.post("/auth/logout", status_code=204)
    def logout(request: Request) -> Response:
        request.app.state.auth_sessions.logout(_opaque(request))
        response = Response(status_code=204)
        security = request.app.state.auth_security
        security.clear(response, security.session_cookie)
        security.clear(response, security.context_cookie)
        return response

    return router


def _opaque(request: Request) -> SecretStr:
    return SecretStr(request.cookies.get(request.app.state.auth_security.session_cookie, ""))


def install_identity_errors(app: FastAPI) -> None:
    for exception, status, code, title in (
        (AuthenticationRejected, 401, "authentication_rejected", "Authentication rejected"),
        (ProviderUnavailable, 503, "auth_unavailable", "Service unavailable"),
        (SessionExpired, 401, "session_expired", "A new login is required"),
        (SessionBusy, 409, "session_busy", "Session renewal is in progress"),
    ):
        # Bind loop values in each handler's defaults; no provider/input text is reflected.
        async def handler(
            request: Request,
            error: Exception,
            status: int = status,
            code: str = code,
            title: str = title,
        ) -> Response:
            response = problem_response(request, status, code, title)
            if isinstance(error, SessionExpired):
                security = request.app.state.auth_security
                security.clear(response, security.session_cookie)
            return response

        app.add_exception_handler(exception, handler)
