"""Canonical corporate role-address manifest shared by API and tooling."""

from __future__ import annotations

from typing import Final


ROLE_ADDRESSES: Final[dict[str, dict[str, str]]] = {
    "contact": {"destination_kind": "odoo_crm", "purpose": "General inquiries and partnerships"},
    "info": {"destination_kind": "odoo_crm", "purpose": "Alias for general inquiries"},
    "support": {"destination_kind": "odoo_helpdesk", "purpose": "Customer and technical support"},
    "help": {"destination_kind": "odoo_helpdesk", "purpose": "Alias for customer support"},
    "sales": {"destination_kind": "odoo_crm", "purpose": "Commercial and sales leads"},
    "privacy": {"destination_kind": "odoo_privacy", "purpose": "Privacy and data-subject requests"},
    "security": {"destination_kind": "security_operations", "purpose": "Security disclosures and incidents"},
    "abuse": {"destination_kind": "security_operations", "purpose": "Spam, phishing, and misuse reports"},
    "postmaster": {"destination_kind": "mail_operations", "purpose": "RFC 2142 mail administration"},
    "billing": {"destination_kind": "odoo_accounting", "purpose": "Invoices and payments"},
    "accounts": {"destination_kind": "odoo_accounting", "purpose": "Alias for accounting"},
    "legal": {"destination_kind": "odoo_legal", "purpose": "Legal, contracts, and regulatory notices"},
    "hr": {"destination_kind": "odoo_hr", "purpose": "Employee relations"},
    "careers": {"destination_kind": "odoo_hr", "purpose": "Recruiting and applications"},
    "noreply": {"destination_kind": "mail_operations", "purpose": "Automated transactional sender"},
    "webmaster": {"destination_kind": "web_operations", "purpose": "Website and portal operations"},
}

OUTBOUND_ROLE_ADDRESSES: Final[frozenset[str]] = frozenset(
    {"contact", "support", "sales", "privacy", "security", "billing", "legal", "hr", "noreply", "webmaster"}
)


def role_address_manifest() -> list[dict[str, str]]:
    return [{"local_part": local_part, **definition} for local_part, definition in ROLE_ADDRESSES.items()]
