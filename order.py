from datetime import datetime, timedelta

from huey import crontab

from .. import config
from ..db import sa
from ..api.constants import CustomerOrderStatus
from ..api.order.models import CustomerOrder, DealerOrder, DealerOrderItem, \
    CustomerOrderStatusHistory, Transaction
from ..api.settings.models import YYMaintainer
from ..api.user.models import SMS
from ..api.order.yyutil import prorate, refund
from ..api.user.models import SMS
from ..utils import decide_dealer_order_411
from .utils import huey, app_context
from .jos import jos, AddOrderError


@huey.periodic_task(crontab())
@app_context
def auto_confirm_orders():
    """Automatically place dealer order to JD

    自动京东下单的类型及时间

    【极速达】Day1 预约 Day1：
    京东自动下单时间 = Min(Day1 15:55, (预约到店时间 - 2h))

    【极速达】Day1 预约 Day2：
    Day1 送：Day2 预约到店时间 - Day2 京东早8:00 < 2h，京东自动下单时间 = Day1 15:55
    Day2 送：同 Day1 预约 Day1

    【极速达】Day1 17:00 之后下单约 Day3（经销商备货不足1h）：
    相当于 Day2 预约 Day3；逻辑与 Day1 预约 Day2 一致

    【次日达】Day1 17:00 之前下单约 Day3（经销商有1h选择备货时间）：
    京东自动下单时间 = Day1 17:55
    """
    auto_confirm_delay = config['CUSTOMER_ORDER_AUTO_CONFIRM_DELAY']
    for order in CustomerOrder.query.join(CustomerOrderStatusHistory).filter(
        CustomerOrder.status == CustomerOrderStatus.PAID,
        CustomerOrderStatusHistory.status == CustomerOrderStatus.PAID,
        CustomerOrderStatusHistory.created_at <
        (datetime.utcnow() - timedelta(minutes=auto_confirm_delay)),
    ):
        try:
            with sa.begin():
                order = CustomerOrder.query.filter(
                    CustomerOrder.id == order.id,
                    CustomerOrder.status == CustomerOrderStatus.PAID,
                ).with_for_update().scalar()
                if not order:
                    continue
                is_411 = decide_dealer_order_411(order, is_task=True)
                if is_411 is None:
                    continue
                order.status = CustomerOrderStatus.CONFIRMED
                do = DealerOrder.create(dealer=order.dealer,
                                        customer_order=order,
                                        is_411=is_411)
                for item in order.items:
                    tyre = item.commodity.tyre
                    if tyre.eclp_stock < item.quantity:
                        raise AddOrderError('京东库存不足')
                    else:
                        tyre.eclp_stock -= item.quantity
                    do.items.append(DealerOrderItem.create(
                        tyre=tyre,
                        quantity=item.quantity,
                    ))
                do.eclp_so_no = jos.add_order(do)
                send_ims_xml(do.ims_xml)
                order.create_sms(config['SMS_CONFIRMED'])
        except AddOrderError:
            SMS.create(
                mobile=config['SMS_PO_MOBILES'],
                text=config['SMS_AUTO_PO_FAILURE'].format(
                    deaer_name=order.dealer.name,
                    order_no=order.order_no,
                ))
            print('DEBUG: failed to order from 3PL')


def send_ims_xml(xml: bytes):
    # TODO
    pass


# @huey.periodic_task(crontab())
# @app_context
# def auto_cancel_pending_orders():
#     """
#     Automatically cancel PENDING orders 15 minutes after creation
#     """
#     auto_cancel_delay = config['CUSTOMER_ORDER_AUTO_CANCEL_DELAY']
#     with sa.begin():
#         CustomerOrder.query.filter(
#             CustomerOrder.status == CustomerOrderStatus.PENDING,
#             CustomerOrder.created_at <
#             (datetime.utcnow() - timedelta(minutes=auto_cancel_delay)),
#         ).update({'status': CustomerOrderStatus.CANCELED})
#         # TODO: https://decentfox.net:10443/issues/6314


@huey.periodic_task(crontab())
@app_context
def auto_confirm_refund_requests():
    """
    Automatically confirm customers' refund requests in 1 day
    """
    auto_confirm_delay = config['CUSTOMER_ORDER_AUTO_REFUND_DELAY']
    for order in CustomerOrder.query.join(CustomerOrderStatusHistory).filter(
        CustomerOrder.status == CustomerOrderStatus.REFUND_REQUESTED,
        CustomerOrderStatusHistory.status ==
        CustomerOrderStatus.REFUND_REQUESTED,
        CustomerOrderStatusHistory.created_at <
        (datetime.utcnow() - timedelta(minutes=auto_confirm_delay)),
    ):
        with sa.begin():
            order.refund_transaction = Transaction.create(
                users_id=order.user.id,
                amount=-order.deposit_amount,
                profile=dict(ref_order_id=order.id),
            )
            order.status = CustomerOrderStatus.REFUNDING
            if refund(order):
                order.create_sms(config['SMS_REFUNDING'])
                order.create_sms(config['SMS_REFUND_PENDING'], False)


@huey.task()
@app_context
def prorate_order(order_id, notify_url):
    order = CustomerOrder.get(order_id)
    result = prorate(order, notify_url)
    if result:
        for i in YYMaintainer.query.filter_by(active=True):
            SMS.create(
                text=config['SMS_YY_LEDGER_ACCOUNT'],
                mobile=i.moible
            )
