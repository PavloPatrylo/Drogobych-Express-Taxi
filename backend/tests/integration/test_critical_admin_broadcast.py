import pytest
from app.db.models import User, UserRole
from app.api.admin.broadcast import _recipient_ids

@pytest.mark.asyncio
async def test_broadcast_recipient_ids_filtering(db_session, admin_user, passenger_user, driver_user):
    # Set telegram_ids for users to ensure they are fetched
    driver_user.telegram_id = 999111
    passenger_user.telegram_id = 888222
    await db_session.commit()

    # 1. Filter ALL recipients
    all_recipients = await _recipient_ids(db_session, trip_id=None, target_group="all")
    assert len(all_recipients) >= 2

    # 2. Filter DRIVERS only
    driver_recipients = await _recipient_ids(db_session, trip_id=None, target_group="drivers")
    assert 999111 in driver_recipients

    # 3. Filter today_passengers (empty for now)
    passenger_recipients = await _recipient_ids(db_session, trip_id=None, target_group="today_passengers")
    assert isinstance(passenger_recipients, list)
