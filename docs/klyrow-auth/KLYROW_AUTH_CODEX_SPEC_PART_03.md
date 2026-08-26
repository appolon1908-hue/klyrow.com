# 6. Suggested application data model

Reuse existing tables when equivalent. Add an additive migration when required.

## `app_users`

```text
id UUID primary key
issuer text not null
subject text not null
email text not null
email_normalized text not null
display_name text
email_verified boolean not null default false
status enum/predicate: pending | active | disabled | deleted
created_at timestamptz not null
updated_at timestamptz not null
last_login_at timestamptz
unique (issuer, subject)
```

Do not make email globally unique unless the business rule and identity-linking design explicitly require it.

## `workspaces`

```text
id UUID primary key
name text not null
slug text not null
status: provisioning | active | suspended | closed
created_at timestamptz not null
updated_at timestamptz not null
unique (slug)
```

## `workspace_memberships`

```text
workspace_id UUID not null
user_id UUID not null
role: owner | admin | developer | analyst | billing | viewer
status: invited | active | suspended
created_at timestamptz not null
unique (workspace_id, user_id)
```

## `postal_workspace_mappings`

```text
workspace_id UUID unique not null
postal_organization_id text
postal_server_id text
status: pending | provisioning | ready | failed
last_error_code text
attempt_count integer not null default 0
updated_at timestamptz not null
```

Do not store Postal secret values in this table.

## `auth_sessions`

Store only hashed or encrypted session material as appropriate. Include revocation, idle expiry, absolute expiry, last-seen timestamp, user agent summary, and IP prefix/audit data according to the privacy policy.

## `auth_audit_events`

Record events such as:

```text
login_succeeded
login_failed
logout
logout_all
session_expired
password_reset_requested
password_changed
email_verification_requested
email_verified
google_identity_linked
google_identity_unlinked
mfa_enabled
mfa_disabled
workspace_created
postal_provisioning_requested
postal_provisioning_succeeded
postal_provisioning_failed
```

Never store passwords, authorization codes, access tokens, refresh tokens, ID tokens, complete verification URLs, or SMTP/API secrets in audit data.

---

# 7. Postal 3.3.7 requirements

## 7.1 Transactional identity email

Use the existing dedicated SMTP-only credential. Do not use a Postal administrator/API credential for authentication email.

Sender:

```text
Klyrow <identity@klyrow.com>
```

Required templates:

- Verify your Klyrow email
- Reset your Klyrow password
- Your Klyrow password was changed
- New sign-in to your Klyrow account
- Google sign-in linked
- Google sign-in removed
- Invitation to a Klyrow workspace
- MFA enabled/disabled

Every template must have HTML and plain-text versions, accessible contrast, a clear expiration statement when applicable, and a security note explaining what to do when the recipient did not request the action.

Use Keycloak's email theme and SMTP integration for identity emails rather than implementing separate application-generated verification/reset tokens.

## 7.2 Postal web-interface OIDC

This is optional and separate from Klyrow customer login.

Postal 3.3.7 can use OIDC for its own web interface. Configure it to use Keycloak only for pre-provisioned Postal users. Postal's OIDC callback format is:

```text
https://<postal-admin-host>/auth/oidc/callback
```

Conceptual configuration:

```yaml
oidc:
  enabled: true
  local_authentication_enabled: true
  name: Klyrow SSO
  issuer: https://auth.codestra.co/realms/codestra
  identifier: <secret-managed-client-id>
  secret: <secret-managed-client-secret>
  scopes:
    - openid
    - profile
    - email
  uid_field: sub
  email_address_field: email
  name_field: name
  discovery: true
```

Do not commit the client secret. Use Postal-supported environment configuration or a root-readable secret-mounted local configuration.

Keep local authentication enabled during the first reviewed OIDC rollout. Disabling it is a separate security change requiring a tested break-glass access procedure and rollback evidence.

Do not expose the Postal administrator UI as the Klyrow customer portal.

---
