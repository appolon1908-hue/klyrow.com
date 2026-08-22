# Klyrow SMTP Guide

Submission listens on private `10.40.0.4:587`. STARTTLS is mandatory and AUTH is unavailable before TLS. Credentials are tenant-bound, Argon2-hashed, displayed once, expiring, rotatable, and revocable. Each credential contains exact allowed sender identities and message streams. Sandbox tenants can address only the internal sink domain or an exact approved test recipient.

Unauthenticated relay, invalid or revoked credentials, cross-tenant senders, suspended senders/domains, unauthorized streams, and arbitrary sandbox Internet recipients are denied. SMTP credentials are not employee passwords.
