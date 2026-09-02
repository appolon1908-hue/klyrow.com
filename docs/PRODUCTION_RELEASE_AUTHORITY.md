# Production release authority

Server 37 launchers accept only a clean Git commit contained by `origin/main`
and the checksummed `klyrow-release-<SHA>` artifact published by the protected
main workflow. Install that artifact into `KLYROW_RELEASE_EVIDENCE_DIR`; do not
re-create its source or image digest files on the server.

After reviewing the secret-file paths and all non-secret runtime settings,
write the single output of `scripts/config-checksum` to the root-owned
`KLYROW_CONFIG_CHECKSUM_FILE`. The checksum binds the fully rendered Compose
configuration without writing its secret-bearing rendering to evidence or
logs.

Before changing a running release, read back its protected source SHA and exact
custom image references. Store those four digest references in the root-owned
`KLYROW_ROLLBACK_DIGESTS_FILE` using this schema:

```json
{
  "source_sha": "40-character-prior-protected-sha",
  "images": {
    "gateway": "ghcr.io/appolon1908-hue/klyrow-gateway@sha256:...",
    "web": "ghcr.io/appolon1908-hue/klyrow-web@sha256:...",
    "migrate": "ghcr.io/appolon1908-hue/klyrow-migrate@sha256:...",
    "postal_provisioner": "ghcr.io/appolon1908-hue/klyrow-postal-provisioner@sha256:..."
  }
}
```

`scripts/verify-release-authority` validates the protected artifact checksums,
source ancestry, Compose/image equality, configuration checksum, prior rollback
set, and post-pull OCI source/revision labels before Compose may replace a
container. A branch SHA, mutable tag, dirty worktree, missing rollback set, or
locally rebuilt image fails closed.
