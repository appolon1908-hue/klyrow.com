#!/usr/bin/env bash
set -Eeuo pipefail

[[ "$EUID" -eq 0 ]] || {
  echo "Mautic migration integration test requires root" >&2
  exit 2
}
[[ "${KLYROW_SOURCE_SHA:-}" =~ ^[0-9a-f]{40}$ ]] || {
  echo "KLYROW_SOURCE_SHA must be the exact tested source SHA" >&2
  exit 2
}

image="klyrow-mautic:${KLYROW_SOURCE_SHA}"
suffix="${GITHUB_RUN_ID:-local}-$$"
legacy_volume="klyrow_mautic_legacy_test_$suffix"
destination_volume="klyrow_mautic_destination_test_$suffix"
manifest_stage=""

cleanup() {
  docker volume rm "$legacy_volume" "$destination_volume" >/dev/null 2>&1 || true
  if [[ -n "$manifest_stage" && "$manifest_stage" == /dev/shm/klyrow-mautic-manifest-test.* ]]; then
    find "$manifest_stage" -mindepth 1 -delete 2>/dev/null || true
    rmdir "$manifest_stage" 2>/dev/null || true
  fi
}
trap cleanup EXIT

tree_digest() {
  local volume="$1"
  local relative="$2"
  docker run --rm \
    --network none \
    --read-only \
    --cap-drop ALL \
    --cap-add DAC_READ_SEARCH \
    --security-opt no-new-privileges \
    --volume "$volume:/data:ro" \
    --entrypoint /bin/sh \
    "$image" -ceu '
      relative="$1"
      root="/data${relative:+/$relative}"
      cd "$root"
      tar --sort=name --mtime="UTC 1970-01-01" --numeric-owner -cf - .
    ' migration-hash "$relative" | sha256sum | awk '{print $1}'
}

docker volume create "$legacy_volume" >/dev/null
docker volume create "$destination_volume" >/dev/null
docker run --rm \
  --network none \
  --volume "$legacy_volume:/legacy" \
  --entrypoint /bin/sh \
  "$image" -ceu '
    mkdir -p /legacy/config
    printf "%s\n" restricted > /legacy/config/restricted.txt
    chown -R www-data:www-data /legacy/config
    chmod 0700 /legacy/config
    chmod 0600 /legacy/config/restricted.txt
  '

docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --cap-add CHOWN \
  --cap-add DAC_OVERRIDE \
  --cap-add FOWNER \
  --security-opt no-new-privileges \
  --volume "$legacy_volume:/legacy:ro" \
  --volume "$destination_volume:/destination" \
  --entrypoint /bin/sh \
  "$image" -ceu '
    cp -a /legacy/config/. /destination/
  '

docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --cap-add DAC_READ_SEARCH \
  --security-opt no-new-privileges \
  --volume "$legacy_volume:/legacy:ro" \
  --volume "$destination_volume:/destination:ro" \
  --entrypoint /bin/sh \
  "$image" -ceu '
    source=/legacy/config/restricted.txt
    destination=/destination/restricted.txt
    test "$(stat -c "%u:%g:%a" "$source")" = \
      "$(stat -c "%u:%g:%a" "$destination")"
    cmp "$source" "$destination"
  '

source_digest="$(tree_digest "$legacy_volume" config)"
destination_digest="$(tree_digest "$destination_volume" "")"
test "$source_digest" = "$destination_digest"

docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --cap-add CHOWN \
  --cap-add DAC_OVERRIDE \
  --cap-add FOWNER \
  --security-opt no-new-privileges \
  --volume "$destination_volume:/destination" \
  --entrypoint /bin/sh \
  "$image" -ceu 'chown 0:0 /destination/restricted.txt'
wrong_owner_digest="$(tree_digest "$destination_volume" "")"
test "$wrong_owner_digest" != "$source_digest"

manifest_stage="$(mktemp -d /dev/shm/klyrow-mautic-manifest-test.XXXXXX)"
printf '%s\n' checkpoint-payload > "$manifest_stage/mautic-persistent-data.tar"
(cd "$manifest_stage" && sha256sum mautic-persistent-data.tar > MANIFEST.sha256)
grep -Eq '^[0-9a-f]{64}  mautic-persistent-data\.tar$' \
  "$manifest_stage/MANIFEST.sha256"
(cd "$manifest_stage" && sha256sum -c MANIFEST.sha256)

echo "Mautic restrictive-ownership migration regression passed."
