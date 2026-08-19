# Google integration

Google OAuth is optional and is not a delivery bypass. Create a Web OAuth client in a controlled Google Cloud project, use an exact HTTPS callback such as `https://app.klyrow.com/v1/integrations/google/callback`, and store client credentials outside Git.

Register exact redirect URIs for every environment; production uses `https://app.klyrow.com/v1/integrations/google/callback`. Request the minimum scopes only when the feature exists: OpenID `openid email profile`; read-only contacts `https://www.googleapis.com/auth/contacts.readonly`; Gmail metadata or send scopes only for explicitly authorized mailbox workflows. Submit sensitive scopes for Google verification.

Encrypt access and refresh tokens at rest, scope them to tenant and Google account, never return refresh tokens to the browser, refresh server-side, and revoke both locally and through Google's revocation endpoint on disconnect. Record consent/audit events without token values. Postal remains the bulk/transactional transport and Gmail quotas must not be bypassed.
