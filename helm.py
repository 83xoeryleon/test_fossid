import base64
from datetime import datetime
from xml.etree import ElementTree as ET

import redis
import requests
from flask import current_app

from .utils import huey, app_context, app
from ..db import sa
from ..api.user.models import SMS

db = redis.Redis(app.config['REDIS_HOST'], app.config['REDIS_PORT'])


def b64encode(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.b64encode(data).decode('utf-8')


def get_access_token():
    token = db.get('HELM_ACCESS_TOKEN')
    if not token:
        refresh_token()
    return token


@huey.task()
@huey.lock_task('helm-token-lock')
@app_context
def refresh_token():
    resp = requests.get(
        current_app.config['HELM_URL'] + '/getToken', headers={
            'dataSource': current_app.config['HELM_DATA_SOURCE'],
            'accountId': current_app.config['HELM_ACCOUNT_ID'],
            'securityKey': current_app.config['HELM_SECURITY_KEY'],
        })
    token = ET.fromstring(resp.text).findtext('accessToken')
    if token:
        db.set('HELM_ACCESS_TOKEN', token,
               ex=current_app.config['HELM_TOKEN_TTL'])


@huey.task()
@app_context
def send_sms(sms_id):
    sms = SMS.get(sms_id)
    if not sms or sms.success:
        return
    token = get_access_token()
    if not token:
        send_sms.schedule((sms_id,), delay=1)
        return
    root = ET.Element('xml')
    ET.SubElement(root, 'smsSource').text = b64encode(
        current_app.config['HELM_SMS_SOURCE'])
    ET.SubElement(root, 'smsType')
    ET.SubElement(root, 'wechatAccountId')
    reqs = ET.SubElement(root, 'sendSmsRequests')
    for mobile in sms.mobile.split(','):
        req = ET.SubElement(reqs, 'sendSmsRequest')
        ET.SubElement(req, 'uniqueID').text = b64encode(str(sms.id))
        ET.SubElement(req, 'senderName')
        ET.SubElement(req, 'recipientMobile').text = b64encode(mobile)
        ET.SubElement(req, 'smsText').text = b64encode(sms.text)
        ET.SubElement(req, 'smsPriority').text = b64encode('5')
    resp = requests.post(current_app.config['HELM_URL'] + '/sendSMSI',
                         data=ET.tostring(root),
                         headers={'accessToken': token})
    res = ET.fromstring(resp.text)
    with sa.transaction():
        sms.handled_at = datetime.utcnow()
        sms.success = res.findtext('isOk') == 'True'
        sms.error = None if sms.success else (res.findtext('errorInfo') or
                                              resp.text)
