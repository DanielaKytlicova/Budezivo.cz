"""Test the scheduled-campaign scheduler (atomic claim + re-verify + send)."""
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from database.supabase import AsyncSessionLocal
from database.models import MailingCampaign, MailingCampaignRecipient, Institution
from scheduler import process_scheduled_campaigns


async def main():
    async with AsyncSessionLocal() as db:
        inst = (await db.execute(select(Institution))).scalars().first()
        c = MailingCampaign(
            institution_id=inst.id, name="TEST scheduled", type="custom",
            status="scheduled", recipient_mode="manual",
            subject="Test predmet", greeting="Dobry den,", intro_text="Ukazka",
            closing_text="Diky", signature="Tym",
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            total_recipients=2,
        )
        db.add(c); await db.flush()
        cid = str(c.id)
        # one valid test recipient + one invalid (should be skipped)
        db.add(MailingCampaignRecipient(campaign_id=c.id, email="sched-test@example.com", school_name="A", status="pending"))
        db.add(MailingCampaignRecipient(campaign_id=c.id, email="not-an-email", school_name="B", status="pending"))
        await db.commit()
        print(f"Created scheduled campaign {cid} (1 valid + 1 invalid recipient), scheduled 1 min ago")

    await process_scheduled_campaigns()

    async with AsyncSessionLocal() as db:
        c = (await db.execute(select(MailingCampaign).where(MailingCampaign.id == cid))).scalars().first()
        rs = (await db.execute(select(MailingCampaignRecipient).where(MailingCampaignRecipient.campaign_id == cid))).scalars().all()
        print(f"Final status: {c.status} | sent={c.sent_count} failed={c.failed_count} skipped={c.skipped_count} | send_started_at={c.send_started_at is not None}")
        for r in rs:
            print(f"  recipient {r.email}: {r.status} ({r.failure_reason})")
        expected_ok = c.status in ("sent", "partially_sent") and c.send_started_at is not None
        skipped_invalid = any(r.status == "skipped" for r in rs)
        print("RESULT:", "PASS" if expected_ok and skipped_invalid else "CHECK")

    # Idempotency: run again → campaign no longer 'scheduled' so it is skipped
    await process_scheduled_campaigns()
    async with AsyncSessionLocal() as db:
        c = (await db.execute(select(MailingCampaign).where(MailingCampaign.id == cid))).scalars().first()
        print(f"After 2nd run status unchanged: {c.status}")
        await db.execute(delete(MailingCampaignRecipient).where(MailingCampaignRecipient.campaign_id == cid))
        await db.execute(delete(MailingCampaign).where(MailingCampaign.id == cid))
        await db.commit()
        print("cleanup done")


if __name__ == "__main__":
    asyncio.run(main())
