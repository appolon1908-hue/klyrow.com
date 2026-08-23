BEGIN;

CREATE TABLE IF NOT EXISTS production_canary_gate (
  gate_key text PRIMARY KEY,
  reserved_deliveries integer NOT NULL DEFAULT 0,
  claimed_deliveries integer NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT production_canary_gate_nonnegative CHECK (reserved_deliveries >= 0),
  CONSTRAINT production_canary_gate_claimed_nonnegative CHECK (claimed_deliveries >= 0),
  CONSTRAINT production_canary_gate_claim_bounds CHECK (claimed_deliveries <= reserved_deliveries)
);

ALTER TABLE production_canary_gate
  ADD COLUMN IF NOT EXISTS claimed_deliveries integer NOT NULL DEFAULT 0;

ALTER TABLE production_canary_gate
  ALTER COLUMN reserved_deliveries SET DEFAULT 0,
  ALTER COLUMN claimed_deliveries SET DEFAULT 0,
  ALTER COLUMN updated_at SET DEFAULT now();

DO $$
BEGIN
 IF EXISTS (
   SELECT 1
     FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'production_canary_gate'
      AND column_name = 'delivered_deliveries'
 ) THEN
   EXECUTE 'UPDATE production_canary_gate '
           'SET claimed_deliveries = LEAST(reserved_deliveries, '
           'GREATEST(claimed_deliveries, delivered_deliveries))';
 END IF;
END $$;

DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='production_canary_gate_claimed_nonnegative' AND conrelid='production_canary_gate'::regclass) THEN
  ALTER TABLE production_canary_gate ADD CONSTRAINT production_canary_gate_claimed_nonnegative CHECK (claimed_deliveries >= 0);
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='production_canary_gate_claim_bounds' AND conrelid='production_canary_gate'::regclass) THEN
  ALTER TABLE production_canary_gate ADD CONSTRAINT production_canary_gate_claim_bounds CHECK (claimed_deliveries <= reserved_deliveries);
 END IF;
END $$;

INSERT INTO production_canary_gate(gate_key, reserved_deliveries, claimed_deliveries, updated_at)
VALUES ('klyrow-single-domain', 0, 0, now())
ON CONFLICT (gate_key) DO NOTHING;

COMMIT;
