# Mail production gate

The approved initial mapping is all fourteen approved domains to disabled
`TEST_SYN`. `codestra.co` is the sole first-promotion candidate. Approval never
implicitly enables sending, receiving, identities, routes, or catch-all rules.

Production promotion is prohibited unless every required gate is `PASS`, all
P0/P1/P2 counts are zero, CI passes, and independent review is approved.
Remaining domains are promoted individually with fresh DNS, identity, inbound,
outbound, recovery, reconciliation, and real-internal-user evidence.

```text
STANDALONE_MAIL_PORTAL
ODOO_AGENT_MAIL_CANARY
STANDALONE_MAIL_CANARY
SHARED_INBOX_CANARY
DOMAIN_CAMPAIGN_SECURITY_MATRIX
MAIL_BACKUP
MAIL_RESTORE
EMAIL_FAILURE_RECOVERY
EMAIL_RECONCILIATION
CURRENT_P0
CURRENT_P1
CURRENT_P2
CI
REVIEW
FINAL_STATUS
```
