# K0-T4 Auth Cluster Verification

Date: 2026-08-30

The five auth refs are contained in the reconciled K0 trunk. The
`feat/klyrow-auth-theme-ui` tip is contained by the
`feat/klyrow-auth-bff-sessions` lineage; the remaining material lineage changes
are represented by the four merge checkpoints below.

Because GitHub had no check runs attached to the historical merge commits, the
complete test suite was replayed at each merge state before K0-T4 was accepted.
No retry-until-green or test modification was used.

| Checkpoint | Reconciled lineage | Result |
|---|---|---:|
| `154b705` | auth BFF sessions, including auth theme UI | 177 passed, 9 warnings |
| `b275f9a` | canonical auth edge routing | 182 passed, 9 warnings |
| `446d882` | auth security stabilization | 193 passed, 9 warnings |
| `1cdfdea` | auth email events integration | 193 passed, 9 warnings |

Containment was also checked directly against the current K0 head:

- `integration/auth-email-events-v1` at `3dac29043c8a98bff36eda58745b1c069d5fec7c`;
- `fix/klyrow-auth-security-stabilization` at `c31c2e8ba6ec977dababb9d2481dffb81e4e6c25`;
- `fix/auth-bff-edge-routing` at `be66757adf5b36d7c723aee408c00af7f7ff69a3`;
- `feat/klyrow-auth-bff-sessions` at `b614012d57d43360cf08b8223a4114c42dd85ce2`;
- `feat/klyrow-auth-theme-ui` at `f953003693d0d6e0e40bb8f4e28b50199382feb4`.

Each tip is an ancestor of the reconciled K0 trunk and has zero commits unique
to its remote ref.

Failures encountered: none.
