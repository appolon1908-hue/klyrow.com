#!/usr/bin/env python3
"""Generate event schemas and AsyncAPI from runtime models, with drift checks."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apps.gateway.app.business_events import DailyUsage, EventEnvelope, KLYROW_EVENTS, SOURCES
from apps.gateway.app.api_standard import components


def documents():
    envelope = EventEnvelope.model_json_schema()
    envelope["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    envelope["$id"] = "https://schemas.codestra.co/events/business-event.v1.schema.json"
    envelope["$defs"] = {"DailyUsage": DailyUsage.model_json_schema()}
    envelope["allOf"] = [{"if": {"properties": {"type": {"const": "klyrow.usage.daily"}}},
                          "then": {"properties": {"data": {"$ref": "#/$defs/DailyUsage"}}}}]
    # Enforce the UTC convention in the portable schema as well as runtime.
    envelope["properties"]["occurred_at"]["pattern"] = r"(?:Z|\+00:00)$"
    daily = DailyUsage.model_json_schema()
    daily["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    daily["$id"] = "https://schemas.codestra.co/events/usage-daily.v1.schema.json"
    example = {"id": "evt_example", "type": "klyrow.usage.daily", "version": 1,
               "source": "klyrow", "tenant_id": "tnt_example",
               "correlation_id": "cor_example", "causation_id": "usage:tnt_example:2026-09-12",
               "occurred_at": "2026-09-13T00:00:00Z",
               "data": {"date": "2026-09-12", "unit": "accepted_message", "quantity": 123,
                        "snapshot_at": "2026-09-13T00:00:00Z"}}
    contract = {"asyncapi": "3.0.0", "info": {"title": "Codestra business events", "version": "1.0.0"},
                "defaultContentType": "application/json", "channels": {}, "operations": {},
                "components": {"messages": {}}}
    for source in SOURCES:
        payload = EventEnvelope.model_json_schema()
        payload["properties"]["source"] = {"const": source}
        if source == "klyrow":
            payload["properties"]["type"]["enum"] = list(KLYROW_EVENTS)
        contract["channels"][source] = {"address": f"codestra.{source}.events",
            "messages": {"event": {"$ref": f"#/components/messages/{source}"}}}
        contract["components"]["messages"][source] = {"name": source+"BusinessEvent", "payload": payload}
        contract["operations"]["receive_"+source] = {"action": "receive", "channel": {"$ref": "#/channels/"+source}}
    return {"contracts/openapi/codestra-components.yaml": {
                "openapi": "3.1.0", "info": {"title": "Codestra API components", "version": "1.0.0"},
                "paths": {}, "components": components()},
            "schemas/json-schema/event-envelope.json": envelope,
            "schemas/json-schema/usage-summary.json": daily,
            "schemas/examples/usage-daily.json": example,
            "schemas/asyncapi/codestra-events.yaml": contract,
            "schemas/asyncapi/klyrow-events.yaml": {**contract,
                "channels": {"klyrow": contract["channels"]["klyrow"]},
                "operations": {"receive_klyrow": contract["operations"]["receive_klyrow"]},
                "components": {"messages": {"klyrow": contract["components"]["messages"]["klyrow"]}}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for name, document in documents().items():
        target = ROOT / name
        value = json.dumps(document, sort_keys=True, indent=2) + "\n"
        if args.check:
            if not target.exists() or target.read_text() != value:
                stale.append(name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value)
    if stale:
        raise SystemExit("Stale event contracts: " + ", ".join(stale))


if __name__ == "__main__":
    main()
