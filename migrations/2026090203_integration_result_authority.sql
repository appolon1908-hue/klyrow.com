BEGIN;

ALTER TABLE integration_results
  DROP CONSTRAINT IF EXISTS integration_results_result_key_key;

ALTER TABLE integration_results
  DROP CONSTRAINT IF EXISTS uq_integration_result_source_key;

ALTER TABLE integration_results
  ADD CONSTRAINT uq_integration_result_source_key
  UNIQUE (tenant_id, source, result_key);

COMMIT;
