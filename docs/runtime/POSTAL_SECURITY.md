# Postal provisioner Debian security snapshot

The Postal base manifest and Ruby dependency lock stay pinned. Debian bookworm,
bookworm-updates and bookworm-security now use the immutable snapshot selector
`20260908T120000Z`, with normal APT archive signature verification. The OS patch
layer checks installed `libssh2-1` is exactly `1.10.0-3+deb12u1`; that remains
the newest published version, so advancing the snapshot does not disturb the
pin.

CI run 34039588419 passed the gateway, web and migration scans, then identified
CVE-2026-58050 and CVE-2026-7598 (HIGH) in the Postal image's
`libssh2-1 1.10.0-3+b1`. Debian confirms the selected update fixes both:

- https://security-tracker.debian.org/tracker/CVE-2026-58050
- https://security-tracker.debian.org/tracker/CVE-2026-7598

The selected snapshot's amd64 Packages index lists
`pool/updates/main/libs/libssh2/libssh2-1_1.10.0-3+deb12u1_amd64.deb`,
SHA-256 `fff72a194e493f88e100a2567e22472bb4ab828d429c2956965c6f2f134f1b3a`.

## Snapshot advance — 2026-09-08 (`linux-libc-dev`)

The `image` job failed on protected `main` at
`16bddf9b3302ad02d6c7a96a7909a3a5a09e52e7` with no source change to the Postal
provisioner. The Trivy scan of `klyrow-postal-provisioner` reported 63 HIGH
findings, all against a single package:

- `linux-libc-dev` installed `6.1.180-1`, fixed in `6.1.187-1`

`linux-libc-dev` ships kernel headers; a container uses the host kernel, so these
are not reachable through the image. The build nevertheless could not take the
fix, because `20260906T000000Z` predates it: the amd64 binary first appears in
`debian-security` at `20260908T094315Z`. The scan turned red without a commit
because the Trivy vulnerability database advanced while the snapshot selector
did not.

Advancing the selector to `20260908T120000Z` lets the existing
`apt-get dist-upgrade -y` layer take `6.1.187-1`. That snapshot's
`bookworm-security` Release is dated `Tue, 08 Sep 2026 11:25:28 UTC`, after the
upload. No Dockerfile logic changes, and the `libssh2-1` assertion is unaffected.

HIGH/CRITICAL scanning, SBOM generation and byte-identical no-cache OCI exports
remain required. This source repair does not publish or deploy an image or
activate Postal, Mautic, email delivery or a volume migration.
