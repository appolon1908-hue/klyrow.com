"""Dedicated Klyrow worker processes with private health endpoints."""

import asyncio
import json
import os
import signal
import uuid
from datetime import timedelta

from sqlalchemy import select

from .billing import BillingEvent, BillingWorkItem, now
from .main import DB, email_outbox_loop, postal_retry_loop
from .provider import (
    dispatch_provider_outbox,
    process_one_sandbox,
    recover_expired_leases,
)
from .security_smtp_worker import security_smtp_delivery_loop

ROLE = os.getenv("KLYROW_WORKER_ROLE", "mail")
RUNNING = True


async def health(reader, writer):
    try:
        await reader.read(4096)
    except Exception:
        pass
    body = json.dumps(
        {"status": "ok", "service": "klyrow-" + ROLE, "role": ROLE}
    ).encode()
    writer.write(
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
        + str(len(body)).encode()
        + b"\r\nConnection: close\r\n\r\n"
        + body
    )
    await writer.drain()
    writer.close()
    await writer.wait_closed()


def billing_tick(max_attempts=8):
    with DB() as session:
        for event in session.scalars(
            select(BillingEvent).order_by(BillingEvent.created_at).limit(200)
        ).all():
            if not session.scalar(
                select(BillingWorkItem).where(
                    BillingWorkItem.billing_event_id == event.id
                )
            ):
                session.add(
                    BillingWorkItem(
                        id=str(uuid.uuid4()),
                        billing_event_id=event.id,
                        tenant_id=event.tenant_id,
                        kind=event.kind,
                    )
                )
        session.commit()
        expired = session.scalars(
            select(BillingWorkItem).where(
                BillingWorkItem.state == "PROCESSING",
                BillingWorkItem.lease_expires_at < now(),
            )
        ).all()
        for item in expired:
            item.state = "DEAD_LETTER" if item.attempts >= max_attempts else "RETRY"
            item.available_at = now() + timedelta(
                seconds=min(900, 2 ** max(item.attempts, 1))
            )
            item.lease_expires_at = None
            item.last_error = "lease_expired"
        session.commit()
        item = session.scalar(
            select(BillingWorkItem)
            .where(
                BillingWorkItem.state.in_(["PENDING", "RETRY"]),
                BillingWorkItem.available_at <= now(),
            )
            .order_by(BillingWorkItem.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not item:
            return 0
        item.state = "PROCESSING"
        item.attempts += 1
        item.lease_expires_at = now() + timedelta(seconds=60)
        session.commit()
        # Commercial mutations are committed atomically by the API. The worker
        # durably acknowledges their immutable event and is safe to replay.
        item = session.get(BillingWorkItem, item.id)
        item.state = "COMPLETED"
        item.completed_at = now()
        item.lease_expires_at = None
        item.last_error = None
        session.commit()
        return 1


async def loop():
    while RUNNING:
        try:
            if ROLE == "mail":
                with DB() as session:
                    recover_expired_leases(session)
                    for _ in range(50):
                        if not process_one_sandbox(session):
                            break
                await dispatch_provider_outbox()
            elif ROLE == "billing":
                billing_tick()
            elif ROLE == "scheduler":
                with DB() as session:
                    session.execute(select(1))
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "level": "error",
                        "service": "klyrow-" + ROLE,
                        "event": "worker_tick_failed",
                        "error": type(exc).__name__,
                    }
                )
            )
        await asyncio.sleep(2 if ROLE != "scheduler" else 10)


async def main():
    global RUNNING
    event = asyncio.Event()

    def stop():
        global RUNNING
        RUNNING = False
        event.set()

    loop_obj = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop_obj.add_signal_handler(sig, stop)
    server = await asyncio.start_server(
        health,
        "0.0.0.0",
        int(os.getenv("KLYROW_WORKER_HEALTH_PORT", "8080")),
    )
    tasks = [asyncio.create_task(loop())]
    if ROLE == "mail":
        tasks.extend(
            [
                asyncio.create_task(postal_retry_loop()),
                asyncio.create_task(email_outbox_loop()),
                asyncio.create_task(security_smtp_delivery_loop()),
            ]
        )
    await event.wait()
    for task in tasks:
        task.cancel()
    server.close()
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
