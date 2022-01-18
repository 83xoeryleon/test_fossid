import functools
import hashlib
import itertools
import logging
import json
from datetime import datetime, timedelta

import requests
from flask import current_app
from huey import crontab

from ..api.constants import DealerOrderStatus
from ..api.order.models import DealerOrder
from ..api.user.models import SMS
from ..api.vehicle.models import Tyre
from ..db import sa
from .utils import huey, app_context

log = logging.getLogger(__name__)
TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S'
MARK_NORMAL = '0' * 28 + '4' + '0' * 9 + '2' + '0' * 11
MARK_411 = '0' * 28 + '4' + '0' * 9 + '9' + '0' * 11


def api(method):
    def wrap(m):
        @functools.wraps(m)
        def wrapper(self, *args, **kwargs):
            return self._run_api(method, m(self, *args, **kwargs))
        return wrapper
    return wrap


class AddOrderError(Exception):
    pass


class JOS:
    def __init__(self):
        pass

    def _run_api(self, method, gen):
        params = json.dumps(gen.send(None), ensure_ascii=False, sort_keys=True)
        params = params.replace(' ', '')
        params = {
            'method': method,
            'access_token': current_app.config['JOS_ACCESS_TOKEN'],
            'app_key': current_app.config['JOS_APP_KEY'],
            'timestamp': (datetime.utcnow() +
                          timedelta(hours=7,
                                    minutes=59)).strftime(TIMESTAMP_FMT),
            'format': 'json',
            'v': '2.0',
            '360buy_param_json': params,
        }
        params = list(map(tuple, params.items()))
        params.sort()
        txt = ''.join(itertools.chain(*params))
        sign = hashlib.md5(txt.encode('utf-8')).hexdigest().upper()
        params.append(('sign', sign))
        resp = requests.get('https://api.jd.com/routerjson', params=params)
        try:
            gen.send(resp.json())
        except StopIteration as e:
            return e.value
        else:
            raise RuntimeError('JOS api not done')

    @api('jingdong.eclp.goods.transportGoodsInfo')
    def create_good(self, product):
        resp = yield {
            'deptNo': current_app.config['JOS_DEPT_NO'],
            'isvGoodsNo': product.mbpn,
            'barcodes': product.mbpn,
            'thirdCategoryNo': current_app.config['JOS_3RD_CAT'],
            'goodsName': product.name,
            'brandNo': product.brand.code,
            'brandName': product.brand.name,
            'produceAddress': product.habitat,
            'standard': product.spec,
            'safeDays': 365 * 5,
            'instoreThreshold': current_app.config['JOS_INSTORE_THRESHOLD'],
            'outstoreThreshold': current_app.config['JOS_OUTSTORE_THRESHOLD'],
            # 'serial': '0',
            # 'batch': '0',
        }
        resp = resp['jingdong_eclp_goods_transportGoodsInfo_response']
        return resp['goodsNo']

    @api('jingdong.eclp.goods.updateGoodsInfo')
    def update_good(self, product):
        resp = yield {
            'deptNo': current_app.config['JOS_DEPT_NO'],
            'goodsNo': product.eclp_no,
            'barcodes': product.mbpn,
            'brandNo': product.brand.code,
            'brandName': product.brand.name,
            'produceAddress': product.habitat,
            'standard': product.spec,
            # 'batch': '0',
        }
        resp = resp['jingdong_eclp_goods_updateGoodsInfo_response']
        return resp['updateResult']

    @api('jingdong.eclp.goods.queryGoodsInfo')
    def query_goods(self, isv_good_nos):
        resp = yield {
            'deptNo': current_app.config['JOS_DEPT_NO'],
            'isvGoodsNos': ','.join(isv_good_nos),
            'queryType': '1',
        }
        resp = resp['jingdong_eclp_goods_queryGoodsInfo_response']
        return dict([(i['isvGoodsNo'], i) for i in resp['goodsInfoList']])

    @api('jingdong.eclp.stock.queryStock')
    def query_stock(self, goods_no=None):
        req = {
            'deptNo': current_app.config['JOS_DEPT_NO'],
            'warehouseNo': current_app.config['JOS_WAREHOUSE_NO'],
            'stockType': '1',
        }
        if goods_no:
            req['goodsNo'] = goods_no
        resp = yield req
        resp = resp['jingdong_eclp_stock_queryStock_response']
        resp = resp['querystock_result']
        if goods_no:
            return resp[0]['v1']['usableNum']
        else:
            return [r['v1'] for r in resp]

    @api('jingdong.eclp.order.addOrder')
    def add_order(self, order):
        items = list(order.items)
        req = {
            'isvUUID': order.uuid,
            'isvSource': current_app.config['JOS_ISV_SOURCE'],
            'shopNo': current_app.config['JOS_SHOP_NO'],
            'departmentNo': current_app.config['JOS_DEPT_NO'],
            'warehouseNo': current_app.config['JOS_WAREHOUSE_NO'],
            'shipperNo': 'CYS0000010',
            'salePlatformSource': '6',
            'soType': '2',
            'consigneeName': order.dealer.consignee_name,
            'consigneeMobile': order.dealer.consignee_mobile,
            'consigneeEmail': order.dealer.consignee_email,
            'addressProvince': order.dealer.consignee_province,
            'addressCity': order.dealer.consignee_city,
            'addressCounty': order.dealer.consignee_county,
            'addressTown': order.dealer.consignee_town,
            'consigneeAddress': order.dealer.consignee_address,
            'consigneePostcode': order.dealer.consignee_postcode,
            'orderMark': MARK_411 if order.is_411 else MARK_NORMAL,
            'customerNo': order.dealer.ims_code,
            'goodsNo': ','.join([item.tyre.eclp_no for item in items]),
            'quantity': ','.join([item.quantity for item in items]),
        }
        if order.customer_order:
            req.update({
                'salesPlatformOrderNo': order.customer_order.order_no,
                'salesPlatformCreateTime':
                    order.customer_order.created_at.strftime(TIMESTAMP_FMT),
            })
        resp = yield req
        try:
            resp = resp['jingdong_eclp_order_addOrder_response']
            return resp['eclpSoNo']
        except KeyError:
            raise AddOrderError(resp)

    @api('jingdong.eclp.order.queryOrder')
    def query_order(self, eclp_so_no):
        resp = yield {
            'eclpSoNo': eclp_so_no,
        }
        resp = resp['jingdong_eclp_order_queryOrder_response']
        return resp['queryorder_result']

    @api('jingdong.ldop.receive.trace.get')
    def query_trace(self, waybill):
        resp = yield {
            'customerCode': current_app.config['JOS_CUSTOMER_CODE'],
            'waybillCode': waybill,
        }
        resp = resp['jingdong_ldop_receive_trace_get_response']
        return resp['querytrace_result']


jos = JOS()


@huey.task()
@app_context
def create_eclp_good(product_id):
    with sa.transaction():
        product = Tyre.query.filter(
            Tyre.id == product_id,
        ).with_for_update().one_or_none()
        if not product:
            return
        product.eclp_no = jos.create_good(product)


@huey.task()
@app_context
def update_eclp_good(product_id):
    with sa.transaction():
        product = Tyre.query.filter(
            Tyre.id == product_id,
            ).with_for_update().one_or_none()
        if not product:
            return
        jos.update_good(product)


@huey.task()
@app_context
def sync_products():
    products_by_mbpn = {}
    for tyre in Tyre.query.filter(Tyre.eclp_no.is_(None)).limit(50):
        products_by_mbpn[tyre.mbpn] = tyre
    if not products_by_mbpn:
        return
    goods = jos.query_goods(products_by_mbpn)
    with sa.transaction():
        for mbpn, good in goods:
            products_by_mbpn.pop(mbpn).eclp_no = good['goodsNo']
    for product in products_by_mbpn.values():
        create_eclp_good(product.id)


@huey.periodic_task(crontab(hour=4, minute=32))
@app_context
def sync_stock():
    stocks = jos.query_stock()
    values = []
    goods_no = []
    for stock in stocks:
        stock_num = stock['usableNum']
        good_no = stock['goodsNo']
        values.append(dict(stock=stock_num, good_no=good_no))
        if stock_num > 0:
            goods_no.append(good_no)
    with sa.transaction():
        sa.session.execute('PREPARE update_stock AS '
                           'UPDATE tyres SET eclp_stock = $1 '
                           'WHERE eclp_no = $2')
        try:
            sa.session.execute(
                sa.text('EXECUTE update_stock (:stock, :good_no)'), values)
        finally:
            sa.session.execute('DEALLOCATE update_stock')
        for po_no, contacts in sa.session.execute('''\
WITH result AS (
    UPDATE tyre_purchase_applications
    SET finished_at = now() at time zone 'utc'
    WHERE finished_at IS NULL
    AND tyre_id IN (
        SELECT id FROM tyres WHERE eclp_no IN ('{}')
    )
    RETURNING id, dealer_id
) SELECT result.id, dealers.profile->>'contacts'
FROM result
LEFT OUTER JOIN dealers
ON result.dealer_id = dealers.id
'''.format('\',\''.join(goods_no))):
            if contacts:
                tos = ','.join([c['mobile'] for c in json.loads(contacts)])
                SMS.create(
                    mobile=tos,
                    text=current_app.config['SMS_PO_DONE'].format(po_no=po_no))


# retry in case db session is not committed
@huey.task(retries=1, retry_delay=3)
@app_context
def create_3pl_order(order_id):
    order = DealerOrder.get(order_id)
    if not order:
        return
    with sa.transaction():
        sa.session.query(
            Tyre.eclp_stock,
        ).filter(
            Tyre.id.in_([item.tyre_id for item in order.items]),
        ).with_for_update().all()
        try:
            eclp_so_no = jos.add_order(order)
            from .order import send_ims_xml
            send_ims_xml(order.ims_xml)
        except AddOrderError:
            SMS.create(
                mobile=current_app.config['SMS_PO_MOBILES'],
                text=current_app.config['SMS_PO_FAILURE'].format(
                    deaer_name=order.dealer.name,
                    dealer_order_no=order.uuid,
                ))
            log.exception('Failed to add 3PL order')
            order.eclp_so_no = 'ERROR'
        else:
            order.eclp_so_no = eclp_so_no
            for item in order.items:
                item.tyre.eclp_stock = max(
                    0, item.tyre.eclp_stock - item.quantity)


@huey.periodic_task(crontab())
@app_context
def refresh_dealer_orders():
    for order_id in sa.session.query(DealerOrder.id).filter(
                    DealerOrder.status == DealerOrderStatus.PENDING):
        query_order(order_id)
        query_trace(order_id)


@huey.task()
@app_context
def query_order(order_id):
    order = DealerOrder.get(order_id)
    if not order or order.status == DealerOrderStatus.DONE:
        return
    if not order.eclp_so_no or order.eclp_so_no == 'ERROR':
        return
    result = jos.query_order(order.eclp_so_no)
    with sa.transaction():
        order.query_order_result = result


@huey.task()
@app_context
def query_trace(order_id):
    order = DealerOrder.get(order_id)
    if not order or order.status == DealerOrderStatus.DONE:
        return
    if not order.waybill:
        return
    result = jos.query_trace(order.waybill)
    with sa.transaction():
        order.query_trace_result = result
