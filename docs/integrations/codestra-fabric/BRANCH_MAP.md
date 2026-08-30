# Klyrow email fabric branch map

```text
feat/klyrow-postal-provisioning
  -> integration/codestra-email-fabric-v2
       -> integration/middleware-email-api-v1
       -> automation/email-event-outbox-v1
       -> feature/email-domain-sender-policy-v1
       -> feature/email-consent-suppression-v1
       -> feature/email-inbound-triage-v1
       -> test/email-fabric-contracts-v1
```

Existing authentication, SECURITY SMTP, Postal-provisioning and runtime-stabilization PRs remain separate and are not rewritten by this branch.