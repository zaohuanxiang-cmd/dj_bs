"""
敏感字段加解密工具

实例账号密码属于敏感信息，不能明文存数据库。
这里用 Fernet（对称加密）：存库前加密，需要使用时再解密。
密钥由 Django 的 SECRET_KEY 派生，换 SECRET_KEY 后旧密文将无法解密。
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _get_fernet():
    """
    根据 SECRET_KEY 生成 Fernet 密钥。

    Fernet 要求密钥是 32 字节再做 urlsafe base64。
    SECRET_KEY 长度不固定，所以先用 SHA256 得到固定 32 字节，再编码。
    """
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_password(plain_text):
    """
    把明文密码加密成字符串，方便存进 TextField。

    :param plain_text: 明文密码
    :return: 加密后的字符串；传入空值时返回空字符串
    """
    if not plain_text:
        return ''
    token = _get_fernet().encrypt(plain_text.encode('utf-8'))
    # Fernet 返回的是 bytes，数据库字段是字符串，需要 decode
    return token.decode('utf-8')


def decrypt_password(cipher_text):
    """
    把库里的密文还原成明文密码。

    密文损坏或密钥不匹配时，返回空字符串，避免任务直接崩溃。
    """
    if not cipher_text:
        return ''
    try:
        plain = _get_fernet().decrypt(cipher_text.encode('utf-8'))
        return plain.decode('utf-8')
    except (InvalidToken, ValueError, TypeError):
        return ''
