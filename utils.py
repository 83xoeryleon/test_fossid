from datetime import datetime, timedelta

from flask import current_app
from pytz import timezone, utc


# noinspection PyPep8Naming
class class_property(property):
    # noinspection PyMethodOverriding
    def __get__(self, instance, owner):
        # noinspection PyArgumentList
        return self.fget(owner)


def to_user_timezone(dt):
    utc_datetime = dt.replace(tzinfo=utc)
    user_timezone = timezone(current_app.config['DEFAULT_TIMEZONE'])
    return utc_datetime.astimezone(user_timezone)


def to_utc_timezone(dt):
    return dt.astimezone(utc)


def decide_dealer_order_411(order, is_task: bool):
    """
    Decide whether a CustomerOrder should trigger a DealerOrder and if 411

    returns True/False if DealerOrder should be 411 or normal
    returns None if auto DealerOrder creation should NOT be triggered
    """
    scheduled_at = to_user_timezone(order.scheduled_at)
    now = to_user_timezone(datetime.utcnow())
    if is_task:  # 自动下单
        if scheduled_at.date() == now.date():
            if now >= min(scheduled_at - timedelta(hours=2),
                          now.replace(hour=15, minute=55)):
                return True
            else:
                return None
        elif scheduled_at.date() == now.date() + timedelta(days=1):
            if (scheduled_at < scheduled_at.replace(hour=10, minute=0) and
                    now >= now.replace(hour=15, minute=55)):
                return True
            else:
                return None
        elif (scheduled_at.date() == now.date() + timedelta(days=2) and
              now >= now.replace(hour=17, minute=55)):
            return False
        return None
    else:  # 经销商手动下单
        if scheduled_at.date() == now.date():
            return True
        elif scheduled_at.date() == now.date() + timedelta(days=1):
            return True
        return False
