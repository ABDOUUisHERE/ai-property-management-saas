from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.contracts import Problem
from app.core.errors import ApplicationError
from app.modules.identity.dependencies import authenticated_profile
from app.modules.identity.repository import Profile
from app.modules.organizations.repository import Organization, Role
from app.modules.organizations.service import OrganizationService

AuthenticatedProfile = Annotated[Profile, Depends(authenticated_profile)]


class CreateOrganization(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=120)
    request_id: UUID

    @field_validator("name")
    @classmethod
    def meaningful_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("Invalid organization name")
        return value


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    role: Role


def _response(organization: Organization) -> OrganizationResponse:
    return OrganizationResponse(id=organization.id, name=organization.name, role=organization.role)


def organization_router() -> APIRouter:
    problems: dict[int | str, dict[str, Any]] = {
        code: {"model": Problem, "content": {"application/problem+json": {}}}
        for code in (401, 403, 404, 409, 413, 422, 429, 500, 503)
    }
    router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"], responses=problems)

    @router.post(
        "",
        status_code=201,
        response_model=OrganizationResponse,
        responses={200: {"model": OrganizationResponse}},
    )
    def create(
        body: CreateOrganization,
        request: Request,
        response: Response,
        profile: AuthenticatedProfile,
    ) -> OrganizationResponse:
        service: OrganizationService = request.app.state.organizations
        organization, created = service.create(profile.id, body.name, body.request_id)
        response.status_code = 201 if created else 200
        response.headers["Cache-Control"] = "no-store"
        return _response(organization)

    @router.get("", response_model=list[OrganizationResponse])
    def list_organizations(
        request: Request, response: Response, profile: AuthenticatedProfile
    ) -> list[OrganizationResponse]:
        service: OrganizationService = request.app.state.organizations
        response.headers["Cache-Control"] = "no-store"
        return [_response(organization) for organization in service.list(profile.id)]

    @router.get("/current", response_model=OrganizationResponse)
    def current(
        request: Request,
        response: Response,
        profile: AuthenticatedProfile,
        x_organization_id: Annotated[UUID | None, Header()] = None,
    ) -> OrganizationResponse:
        if x_organization_id is None:
            raise ApplicationError(422, "organization_required", "Select an organization")
        service: OrganizationService = request.app.state.organizations
        authorized = service.current(profile.id, x_organization_id)
        response.headers["Cache-Control"] = "no-store"
        return _response(authorized.organization)

    return router
