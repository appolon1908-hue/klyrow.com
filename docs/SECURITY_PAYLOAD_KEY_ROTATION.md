# Klyrow SECURITY payload key lifecycle

Klyrow SECURITY mail may contain verification codes, recovery links, and other identity-security content. Queued MIME is encrypted only for the bounded retry window and is purged after provider submission, terminal dead-letter, or retention expiry.

## Keyring format

`KLYROW_SECURITY_PAYLOAD_KEY_FILE` is a root-owned runtime secret. It is not committed to Git. The file contains one Fernet key per non-empty line:

```text
<active key>
<previous decrypt-only key>
<older decrypt-only key>
```

The first key encrypts new SECURITY payloads. New payloads record only a non-secret SHA-256-derived `key_id`; key material is never written into message metadata, logs, database payloads, or provider requests.

## Rotation procedure

1. Generate the replacement key in the approved secret-management system.
2. Prepend it to the runtime key file while retaining the previous key(s).
3. Restart/reload the SMTP relay and SECURITY worker through the reviewed immutable deployment path.
4. Verify new queued messages carry the new `key_id` and can be decrypted by the worker.
5. Verify pre-rotation ciphertext still decrypts while the old key remains.
6. Wait at least the maximum SECURITY payload retention/retry window plus an operational safety margin.
7. Confirm no queued, leased, retry, sandbox-delivered, or dead-letter SECURITY records reference the old `key_id`.
8. Remove the retired key from the runtime secret and deploy the same reviewed configuration path.

Never remove an old key merely because a new key is active. Missing decryption keys fail closed and the worker must not silently discard or deliver undecryptable SECURITY mail.

## Secret-management target

The runtime secret file may be populated from a managed KMS/Vault/HSM-backed secret workflow. The application code intentionally consumes only the mounted keyring file so provider-specific secret-manager credentials are not embedded in the SMTP relay or committed to this repository.

Production rotation requires change approval, exact artifact identity, rollback evidence, and post-rotation delivery/recovery testing. It does not change the `KLYROW_SECURITY_SMTP_ENABLED` or `KLYROW_SECURITY_SMTP_LIVE_ENABLED` gates.
