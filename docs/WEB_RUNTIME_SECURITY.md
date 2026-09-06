# Web runtime package authority

The Nginx base remains pinned by its manifest digest. Runtime patches are official
Alpine v3.24 x86_64 APKs stored in `apps/web/vendor`, bound by `SHA256SUMS`,
and verified with the base image's Alpine signing keys before offline installation.
The final process remains UID 101. Package logs are removed for reproducible OCI exports.

On 2026-09-06, CI run 34033739986 for source `515bfdae7fcc93e08544ba7aec8f58f6c3220ac0`
reported seven HIGH findings in the **web** image's `libuuid 2.42.1-r0`:
CVE-2026-53612, CVE-2026-53613, CVE-2026-53614, CVE-2026-76642,
CVE-2026-78408, CVE-2026-78409, and CVE-2026-78410.
The report requires `2.42.3-r1` to cover all seven. Patching the separate migration
image cannot repair the web image.

Package source: https://dl-cdn.alpinelinux.org/alpine/v3.24/main/x86_64/libuuid-2.42.3-r1.apk

SHA-256: `8306e5bb577696c9069fe1dfd9e1dcc39d2d481c6a1b0e707fd03c3e21aa6aa2`.

The build verifies the installed version. CI must still pass the HIGH/CRITICAL
scan, image smoke checks, SBOM generation, and two no-cache byte-identical OCI
exports before release. No vulnerability exception or delivery activation is added.
