import base64
from hashlib import md5
import json
import urllib.parse

# noinspection PyUnresolvedReferences,PyProtectedMember
from cryptography.hazmat.bindings._openssl import ffi, lib
import requests

from ... import config
from ...db import sa
from .. import JSONEncoder
from ..constants import TransactionStatus
from ..utils import external_url_for

_pubkey = None


def _get_pubkey():
    global _pubkey
    if _pubkey:
        return _pubkey
    pubkey_pem = (
        b'-----BEGIN PUBLIC KEY-----\n' +
        config['YY_PUBLIC_KEY'].encode('utf-8') +
        b'\n-----END PUBLIC KEY-----\n'
    )
    data_char_p = ffi.new("char[]", pubkey_pem)
    bio = lib.BIO_new_mem_buf(data_char_p, len(pubkey_pem))
    pubkey = lib.PEM_read_bio_PUBKEY(
        ffi.gc(bio, lib.BIO_free), ffi.NULL, ffi.NULL, ffi.NULL)
    if pubkey == ffi.NULL:
        raise Exception('Invalid YY pub key')
    _pubkey = lib.EVP_PKEY_get1_RSA(pubkey)
    return _pubkey


def _encrypt(info: dict) -> bytes:
    pubkey = _get_pubkey()
    size = lib.RSA_size(pubkey)
    result = b''
    data = JSONEncoder(
        ensure_ascii=False, sort_keys=True
    ).encode(info).encode('utf-8')
    while data:
        buf = ffi.new("unsigned char[]", size)
        lib.RSA_public_encrypt(len(data[:int(size / 2)]), data, buf, pubkey,
                               lib.RSA_PKCS1_PADDING)
        result += ffi.buffer(buf)[:]
        data = data[int(size / 2):]
    return base64.encodebytes(result).strip()


def _decrypt(info: str) -> dict:
    pubkey = _get_pubkey()
    size = lib.RSA_size(pubkey)
    data = urllib.parse.unquote(info)
    data = base64.decodebytes(data.encode('utf-8'))
    result = b''
    while data:
        buf = ffi.new("unsigned char[]", int(size / 2))
        lib.RSA_public_decrypt(size, data, buf, pubkey, lib.RSA_PKCS1_PADDING)
        result += ffi.buffer(buf)[:]
        data = data[size:]
    result = result.strip(b'\x00')
    return json.loads(result)


def _get_url(info: dict):
    key = config['YY_KEY']
    str_to_sign = ('&'.join(sorted(f'{k}={v}' for k, v in info.items())) +
                   f'&key={key}')
    info['sign'] = md5(str_to_sign.encode('utf-8')).hexdigest().upper()

    return '{}?info={}'.format(
        config['YY_GATEWAY'],
        urllib.parse.quote(_encrypt(info)))


def get_payment_url(order, pay_method) -> str:
    return _get_url(dict(
        service='pay.auth.pay.apply',
        appid=config['YY_APPID'],
        out_trade_no=order.order_no,
        total_fee=order.deposit_amount,
        seller_user_id=order.dealer.yy_seller_user_id,
        notify_url=external_url_for('daimler.web.yy_pay_notify_url'),
        return_url=external_url_for('daimler.web.yy_pay_return_url'),
        limit_pay=pay_method,
        subject=f'{order.items[0].tyre_name} 轮胎快修服务订金',
    ))


def refund(order) -> bool:
    url = _get_url(dict(
        service='pay.auth.refund.apply',
        appid=config['YY_APPID'],
        out_trade_no=order.order_no,
        notify_url=external_url_for('daimler.web.yy_refund_notify_url'),
    ))
    resp = parse_info(requests.get(url).text)
    with sa.begin():
        order.refund_transaction.yy_response = resp
        if resp.get('code', 0) in ('200', '601', '603', '605'):
            return True
        else:
            order.refund_transaction.status = TransactionStatus.FAILURE
            return False


def prorate(order, notify_url) -> bool:
    # notify_url: prorate will be run in worker, who doesn't know the host name
    url = _get_url(dict(
        service='pay.auth.prorate.apply',
        appid=config['YY_APPID'],
        out_trade_no=order.order_no,
        notify_url=notify_url,
    ))
    resp = parse_info(requests.get(url).text)
    order.transaction.yy_prorate_response = resp
    with sa.begin():
        if resp.get('code', 0) in ('200', '601', '603', '605'):
            order.transaction.status = TransactionStatus.PRORATING
            return True
        else:
            order.transaction.status = TransactionStatus.FAILURE
            return False


def parse_info(info):
    return _decrypt(info)
