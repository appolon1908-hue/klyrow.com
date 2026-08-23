BEGIN;

ALTER TABLE klyrow_invoices
  ADD COLUMN IF NOT EXISTS request_key varchar;

CREATE UNIQUE INDEX IF NOT EXISTS uq_klyrow_invoice_request_key
  ON klyrow_invoices (tenant_id, request_key)
  WHERE request_key IS NOT NULL;

COMMIT;
