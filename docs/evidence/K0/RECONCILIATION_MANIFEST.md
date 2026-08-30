# K0 Reconciliation Manifest

Snapshot taken on 2026-08-30 before branch deletion. The mission expected 66
non-`main` refs; 70 were present at the deletion boundary. The four additional
refs were `codex/klyrow-smtp-integration-files`,
`docs/repository-profile-v1`, `phase-k0/trunk-reconciliation`, and
`phase-s0/contract-conformance`. They are included below rather than silently
excluded from the gate. After the initial snapshot,
`phase-s0/contract-conformance` advanced by one documentation-only gate-evidence
commit; that new tip was re-audited and merged before deletion.

The `phase-k0/trunk-reconciliation` row records the remote execution-branch tip
immediately before the final S0 evidence reconciliation. Commits which update
this manifest necessarily advance that same branch, so its immutable final head
is also preserved by PR #50 and the protected-branch squash audit trail.

## Summary

- Baseline: `main@6ff3d5176dadf336d5b357723363bd1c171a0450`
- Trunk candidate: `feat/klyrow-postal-provisioning@e5b8791d0d9c652b084943c5b5fb765b2b32e811`
- Candidate verification: 177 tests passed in a fresh Linux-style environment;
  see [CANDIDATE_VERIFICATION.md](CANDIDATE_VERIFICATION.md).
- Final collected inventory before the clean-checkout gate: 226 tests.
- 73/15 cluster: all seven refs had the identical tip
  `519ad72b31307d8bd34a13eefbf65a15bd6ea3e9`; merged once and recorded for
  every alias.
- Auth cluster: all five refs were reconciled with a full-suite run after each
  material tree change. The integration aggregate was history-only after its
  parents were reconciled.
- Dependencies: `dnspython==2.7.0` and `aiosmtpd==1.4.6` are pinned in
  `apps/gateway/requirements.txt`, and CI installs that file before running the
  complete `tests` directory.
- Dispositions: 39 `merged`, 26 `preserved-as-issue #21`, and 5
  `preserved-as-issue #49`.
- `KLYROW_SAFE_MODE` and `KLYROW_PRODUCTION_GATE_APPROVED` defaults were not
  changed by K0.

The roadmap preservation record, including exact branch tips, is in
[#21](https://github.com/appolon1908-hue/klyrow.com/issues/21#issuecomment-5468906575).
The legacy provider/inbound selective-port record is
[#49](https://github.com/appolon1908-hue/klyrow.com/issues/49).

## Branch dispositions

| Branch | Tip SHA | Disposition | Evidence / reason |
|---|---|---|---|
| `agent/api-production-readiness-20260822` | `3cfe31fac177ededf0f0e93bca7121ea1980ffc5` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `agent/certification-ledger-migration` | `d5777a8afaa6954d35462e08d4d4153f0164b308` | preserved-as-issue [#49](https://github.com/appolon1908-hue/klyrow.com/issues/49) | Unique older provider/inbound delta requires a selective port, not a whole-tree merge. |
| `agent/codestra-production-remediation` | `f88ba36e76a9395b9aec1b8f90afb997dad1cad2` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `agent/event-campaign-remediation-20260823` | `be30ab82ae1a96ea944cd031317054e7b7e19d83` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `agent/inbound-routing-20260823` | `6117bb1a5a0c1b041c7e4b34f1a9cacc9d401adc` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `agent/klyrow-complete-saas-20260822` | `198ab2957a061c3c745d775e0010bd429295adfd` | preserved-as-issue [#49](https://github.com/appolon1908-hue/klyrow.com/issues/49) | Unique older provider/inbound delta requires a selective port, not a whole-tree merge. |
| `agent/klyrow-mail-engine-integration` | `4f8005748b92b1b538335bda8e59538dc287346f` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `agent/klyrow-migration-certification` | `5dc9b32328c231aea575a0d0059bc4baf527e546` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `agent/klyrow-smtp-production-readiness` | `160930f7693667e1ff8b14f04acd7f22e092af77` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `agent/postal-inbound-production-20260823` | `ad432f9bf598a629be2ca23c3663f7feb4064c81` | preserved-as-issue [#49](https://github.com/appolon1908-hue/klyrow.com/issues/49) | Unique older provider/inbound delta requires a selective port, not a whole-tree merge. |
| `agent/postal-native-inbound-20260823` | `c0035709dc6ca1efb3c7cc29c76894c604890318` | preserved-as-issue [#49](https://github.com/appolon1908-hue/klyrow.com/issues/49) | Unique older provider/inbound delta requires a selective port, not a whole-tree merge. |
| `agent/production-email-platform` | `9187b2a7cb63bc925601f5c2a542c6dd3cd2be56` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `automation/email-event-outbox-v1` | `519ad72b31307d8bd34a13eefbf65a15bd6ea3e9` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `codex/klyrow-smtp-integration-files` | `f2044cf67ff75038c2d79d74e690e3704ebb8948` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `docs/api-audit-20260827` | `34a73bf0bf2a5f6dc2aea5ab4ca44a9ae9d5de0f` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `docs/communications-platform-authority` | `382cfc5f9817aac5484adcd2ea05fd207da1c146` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `docs/klyrow-auth-codex-spec` | `4d2acd47a6e3d39845de6c9dfdb8b35bb5ff697e` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `docs/repository-authority-20260829` | `76ca92d4268c19662184799f7be7da26a8c91e3e` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `docs/repository-profile-v1` | `e415a391d7755f53901b87f593e0741f9fbd3bc2` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feat/beyvra-transactional-email` | `ce5c03263ad34d37f9b8eeb5afbb1a906e3bb4a3` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feat/communications-api-v1-email-provider` | `15b14b63d2f17a74091702d9f6ddc5787237e317` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feat/keycloak-security-mail-hardening` | `70b85f36971a4bc4d10de02124b9980a1c5b28a6` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feat/keycloak-security-smtp-delivery` | `33d16dfe09da0e33c727a47b6ba7fd87867d88f5` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feat/klyrow-ai-assist` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-analytics-attribution` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-auth-bff-sessions` | `b614012d57d43360cf08b8223a4114c42dd85ce2` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feat/klyrow-auth-theme-ui` | `f953003693d0d6e0e40bb8f4e28b50199382feb4` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feat/klyrow-billing-plans-usage` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-consent-preferences` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-content-studio` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-control-plane-events` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-cross-channel-contract` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-customer-data-events` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-decision-policy-ledger` | `ad226912eacbbcbc56458af75b056d11fdb8f148` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-deliverability` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-developer-platform` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-enterprise-admin` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-experimentation` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-integrations` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-journeys-automation` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-observability-sre` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-odoo-backoffice-sync` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-postal-provisioning` | `e5b8791d0d9c652b084943c5b5fb765b2b32e811` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feat/klyrow-provider-mesh-portability` | `2f7786355d89014efc56757d006d86b5574cd2d6` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-recipient-trust-center` | `bad4ef3b21f76006dd27093612f83f0a9c4939ea` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-reconciliation-self-healing` | `11a79c47e4b4322a33a22075854fe2306c4b3979` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-reliability-ha` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-reseller-white-label` | `b25a195a963a303a6607511663c3a051ecf32193` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-security-hardening` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-segmentation` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-simulation-attention-engine` | `32f2ab3bba064cdb08a94621305294e523af0fa7` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-stream-separation` | `a6ba31e6cd95acb6c6c23f9876e542e95e3bc38e` | preserved-as-issue [#21](https://github.com/appolon1908-hue/klyrow.com/issues/21) | Roadmap/planning ref; exact tip recorded in the K0 preservation comment. |
| `feat/klyrow-tenancy-onboarding` | `1a2709aa8ffb8da9cb6f1432309edf6e5c6ad59c` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feat/security-mail-kms-contract` | `a696ae1c5e3ea5cac0f40ee56846caca2cdca646` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feature/email-consent-suppression-v1` | `519ad72b31307d8bd34a13eefbf65a15bd6ea3e9` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feature/email-domain-sender-policy-v1` | `519ad72b31307d8bd34a13eefbf65a15bd6ea3e9` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `feature/email-inbound-triage-v1` | `519ad72b31307d8bd34a13eefbf65a15bd6ea3e9` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `fix/auth-bff-edge-routing` | `be66757adf5b36d7c723aee408c00af7f7ff69a3` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `fix/klyrow-auth-security-stabilization` | `c31c2e8ba6ec977dababb9d2481dffb81e4e6c25` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `fix/production-gaps-1-10` | `59e58d39f0a67c39219c76579d94e6e00766e736` | preserved-as-issue [#49](https://github.com/appolon1908-hue/klyrow.com/issues/49) | Unique older provider/inbound delta requires a selective port, not a whole-tree merge. |
| `fix/security-smtp-runtime-wiring` | `9befe7498ffa9d87167fbf6c001c6a683a71b057` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `integration/auth-email-events-v1` | `3dac29043c8a98bff36eda58745b1c069d5fec7c` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `integration/codestra-email-fabric-v2` | `519ad72b31307d8bd34a13eefbf65a15bd6ea3e9` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `integration/middleware-email-api-v1` | `519ad72b31307d8bd34a13eefbf65a15bd6ea3e9` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `ops/website-provider-host-edge` | `e070758e14aff702b6b45a7a500c2c23fdd445d8` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `phase-k0/trunk-reconciliation` | `4d381b0b6cefe7b7c1f3e7d992e92b1fe68e58c2` | merged | Pre-finalization execution tip; subsequent commits only reconcile post-snapshot evidence and this manifest. The final head remains preserved by PR #50. |
| `phase-s0/contract-conformance` | `5693fde3d13c633e63615cda3738532c3a046dff` | merged | The post-snapshot S0 gate-evidence commit was re-audited and merged; this tip is an ancestor of the reconciled K0 trunk. |
| `planning/corporate-email-saas-1-12` | `8460dad391858a35ea156e6e92823b6553d82260` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `release/klyrow-production-readiness` | `ebf54de55d87868818bb518872d0804741e33d52` | merged | Tip is an ancestor of the reconciled K0 trunk. |
| `test/email-fabric-contracts-v1` | `519ad72b31307d8bd34a13eefbf65a15bd6ea3e9` | merged | Tip is an ancestor of the reconciled K0 trunk. |

## Deletion rule

Every non-`main` ref in the snapshot above has one of the mission-approved
dispositions. No ref may be deleted if its current remote tip differs from this
manifest; a changed or newly created ref requires a new manifest entry and a
fresh disposition.
