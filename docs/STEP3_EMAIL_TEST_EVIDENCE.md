# Step 3 Email Test Evidence

Date: 2026-08-29

## Passing Local Evidence

```text
python -m pytest tests/test_communications_provider.py -q
2 passed, 9 warnings
```

## Full Suite Status

```text
python -m pytest -q
131 passed, 4 failed
```

The observed failures are not caused by the Step 3 canonical provider path:

- `tests/test_backup_encryption.py::test_encrypted_backup_restore_round_trip`: `gpg` is not installed in the local Windows environment.
- `tests/test_provider.py::test_dkim_private_key_protection_and_rotation`: POSIX `0600` file-mode assertion does not hold on Windows.
- `tests/test_provider.py::test_domain_execution_dns_matrix_requires_single_spf_and_dmarc`: cascades from the DKIM rotation test failing before active-key state is established.
- `tests/test_provider_schema_contract.py::test_released_provider_registry_migration_remains_immutable`: existing migration hash mismatch with no local diff in `migrations/008_provider_saas_registry_separation.sql`.

Linux CI must rerun the full suite before Step 3 is certified.
