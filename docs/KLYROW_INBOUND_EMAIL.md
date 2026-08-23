# Klyrow Inbound Email

Inbound flow is Postal → authenticated provider endpoint → exact enabled/verified address route → tenant destination event. No global catch-all exists. Client-supplied destination overrides are denied.

MIME parsing covers plain text, HTML, multipart bodies, attachments, Message-ID, threading headers, addressing, and date. Provider-event ID plus tenant and Message-ID plus route prevent duplicates. Limits apply before persistence; unsafe paths are rejected and executable attachments are quarantined. Malware scanning can be inserted before an item leaves quarantine.

The authenticated inbound adapter supplies its provider spam score. Tenant policy defines separate quarantine and reject thresholds and maps the score to `ACCEPT`, `QUARANTINE`, or `REJECT`. The reject threshold must be strictly greater than the quarantine threshold. A browser or arbitrary SMTP header is never treated as the authoritative score.
