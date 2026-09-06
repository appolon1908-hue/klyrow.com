# Mutation capability enforcement

Authentication establishes a principal and tenant. It does not grant every
write operation. The shared `capabilities` module preserves the existing
canonical role and explicit permission/scopes policy from `production_api`.
The old helper imports remain compatible for existing callers.

The following formerly authentication-only mutation paths now check the
capability before looking up state, changing rows, accessing key material, or
resolving DNS:

| Mutations | Capability |
| --- | --- |
| Contact list create, edit, delete | `contact.manage` |
| Template create, update, publish, rollback, delete | `template.manage` |
| Campaign definition create, test, schedule, cancel | `campaign.manage` |
| Product domain claim, verify, DKIM rotate | `domain.manage` |
| Provider domain register, verify, DNS check, suspend, DKIM verify | `domain.manage` |
| Product/provider sender creation and provider sender suspension | `sender.manage` |
| Provider SMTP credential rotation and revocation | `credential.manage` |

The existing contact, campaign, suppression, Mautic, and operation-control
guards continue using the same policy. Existing stricter administrator/service
requirements remain in place. Authentication, audience validation, and
tenant-scoped queries remain required; adding a capability cannot grant access
to another tenant's resources. The internal provider API receives these guards
as well as the product API.

READ_ONLY, ANALYST, BILLING, and unprivileged service identities are denied
when the required capability is absent. A service with an explicit exact grant
can perform the corresponding operation. Contact-list responses are encoded
after refreshing the committed row, so authorized create/update/read operations
return usable JSON instead of an ORM serialization error.

`tests/test_mutation_capabilities.py` tests denial before state access across
the affected handlers, authorized list CRUD, permission revocation, tenant
isolation, and exact domain grants through the real HTTP routes. No schema,
identity-provider, production-secret, or runtime activation changes are needed.
Rollback should retain the guards; removing them restores unauthorized writes.
