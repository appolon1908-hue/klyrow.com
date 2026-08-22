# Klyrow Shared Server Boundary

In scope: Klyrow gateway/provider, SMTP relay, Postal integration, Klyrow database metadata, mail monitoring, and mail-only proxy/TLS configuration.

Out of scope: Telnexa, Jasmin, SMPP connectors/routes/credentials, SMS API/workers, and every Telnexa billing component/database. Capture container IDs, health, restart counts, connector/routes state, and configuration fingerprints before and after every Klyrow deployment. Any drift fails the release.
