"""Organization bootstrap and current membership are the tenant authorization seam."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.core.context import Clock, TenantContext
from app.core.errors import ApplicationError
from app.modules.organizations.repository import Organization, OrganizationRepository


@dataclass(frozen=True)
class AuthorizedOrganization:
    organization: Organization
    context: TenantContext


class OrganizationService:
    def __init__(self, repository: OrganizationRepository, clock: Clock):
        self._repository, self._clock = repository, clock

    def create(self, actor_id: UUID, name: str, request_id: UUID) -> tuple[Organization, bool]:
        organization_id = uuid4()
        with self._repository.transaction(actor_id, bootstrap_id=organization_id) as tx:
            created = tx.create(organization_id, name, request_id, self._clock.now())
            if created:
                tx.first_owner(organization_id, self._clock.now())
            organization = tx.created(request_id)
            if organization is None or organization.name != name:
                raise ApplicationError(
                    409, "organization_conflict", "Organization request conflicts"
                )
        return organization, created

    def list(self, actor_id: UUID) -> list[Organization]:
        with self._repository.transaction(actor_id) as tx:
            return tx.list()

    def current(self, actor_id: UUID, selector: UUID) -> AuthorizedOrganization:
        with self._repository.transaction(actor_id) as tx:
            organization = tx.current(selector)
        if organization is None:
            raise ApplicationError(404, "organization_not_found", "Organization not found")
        return AuthorizedOrganization(
            organization, TenantContext(organization.id, actor_id, principal="user")
        )
