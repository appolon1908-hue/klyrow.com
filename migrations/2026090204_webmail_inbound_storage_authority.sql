BEGIN;

ALTER TABLE webmail_mailboxes
  ADD COLUMN IF NOT EXISTS storage_used_bytes bigint NOT NULL DEFAULT 0;

ALTER TABLE webmail_mailboxes
  DROP CONSTRAINT IF EXISTS webmail_mailbox_storage_used_valid;

ALTER TABLE webmail_mailboxes
  ADD CONSTRAINT webmail_mailbox_storage_used_valid
  CHECK (storage_used_bytes >= 0);

ALTER TABLE webmail_attachments
  DROP CONSTRAINT IF EXISTS uq_webmail_attachment_message_digest_name;

-- Only authenticated provider ingress is quota-accounted. Rebuild the counter
-- from durable rows so upgrade, restore, and replay all start from the same
-- authority without trusting a prior application-maintained value.
WITH message_bytes AS (
  SELECT
    mailbox_id,
    COALESCE(SUM(
      octet_length(COALESCE(subject, '')) +
      octet_length(COALESCE(text_body, '')) +
      octet_length(COALESCE(html_body, ''))
    ), 0)::bigint AS bytes
  FROM webmail_messages
  WHERE direction = 'INBOUND' AND deleted_at IS NULL
  GROUP BY mailbox_id
), attachment_bytes AS (
  SELECT
    message.mailbox_id,
    COALESCE(SUM(attachment.size), 0)::bigint AS bytes
  FROM webmail_messages AS message
  JOIN webmail_attachments AS attachment ON attachment.message_id = message.id
  WHERE message.direction = 'INBOUND' AND message.deleted_at IS NULL
  GROUP BY message.mailbox_id
)
UPDATE webmail_mailboxes AS mailbox
SET storage_used_bytes = COALESCE(message_bytes.bytes, 0) + COALESCE(attachment_bytes.bytes, 0)
FROM message_bytes
FULL OUTER JOIN attachment_bytes USING (mailbox_id)
WHERE mailbox.id = COALESCE(message_bytes.mailbox_id, attachment_bytes.mailbox_id);

UPDATE webmail_mailboxes
SET storage_used_bytes = 0
WHERE id NOT IN (
  SELECT mailbox_id FROM webmail_messages
  WHERE direction = 'INBOUND' AND deleted_at IS NULL
);

COMMIT;
