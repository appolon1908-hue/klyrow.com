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

cleanup() {
  docker volume rm "$legacy_volume" "$destination_volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT

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

echo "Mautic restrictive-ownership migration regression passed."
