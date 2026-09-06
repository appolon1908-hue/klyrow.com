# Postal provisioner Debian security snapshot

The Postal base manifest and Ruby dependency lock stay pinned. Debian bookworm,
bookworm-updates and bookworm-security now use the immutable snapshot selector
`20260906T000000Z`, with normal APT archive signature verification. The OS patch
layer checks installed `libssh2-1` is exactly `1.10.0-3+deb12u1`.

CI run 34039588419 passed the gateway, web and migration scans, then identified
CVE-2026-58050 and CVE-2026-7598 (HIGH) in the Postal image's
`libssh2-1 1.10.0-3+b1`. Debian confirms the selected update fixes both:

- https://security-tracker.debian.org/tracker/CVE-2026-58050
- https://security-tracker.debian.org/tracker/CVE-2026-7598

The selected snapshot's amd64 Packages index lists
`pool/updates/main/libs/libssh2/libssh2-1_1.10.0-3+deb12u1_amd64.deb`,
SHA-256 `fff72a194e493f88e100a2567e22472bb4ab828d429c2956965c6f2f134f1b3a`.

HIGH/CRITICAL scanning, SBOM generation and byte-identical no-cache OCI exports
remain required. This source repair does not publish or deploy an image or
activate Postal, Mautic, email delivery or a volume migration.
