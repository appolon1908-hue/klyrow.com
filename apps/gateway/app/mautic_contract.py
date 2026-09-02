"""Single command vocabulary shared by the Mautic API and dispatcher."""

SUPPORTED_MAUTIC_COMMANDS = frozenset(
    {
        "contact.upsert.v1",
        "contact.delete.v1",
        "segment.upsert.v1",
        "segment.delete.v1",
        "campaign.upsert.v1",
        "campaign.delete.v1",
        "campaign.publish.v1",
        "campaign.pause.v1",
        "campaign_membership.add.v1",
        "campaign_membership.remove.v1",
        "segment_membership.add.v1",
        "segment_membership.remove.v1",
        "email_campaign.state.v1",
        "webhook.register.v1",
        "sync.request.v1",
        "form_submissions.read.v1",
    }
)
