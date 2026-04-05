"""Identity CRUD repositories."""

from identity_service.crud.delegated_issuers import delegated_issuer_repository
from identity_service.crud.mappings import mapping_repository
from identity_service.crud.principals import principal_repository
from identity_service.crud.tenant_domains import tenant_domain_repository
from identity_service.crud.token_records import token_record_repository

__all__ = [
    "tenant_domain_repository",
    "principal_repository",
    "delegated_issuer_repository",
    "mapping_repository",
    "token_record_repository",
]
