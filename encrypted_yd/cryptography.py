"""Модуль для описания криптоалгоритмов, используемых для работы с YD.

В настоящее время используется сторонний пакет "pyсryptodome". Тем не менее, в дальнейшем возможно использование других,
в том числе, самописных криптографических пакетов, модулей, алгоритмов, соответствующих описанному здесь интерфейсу.
"""

from abc import ABC, abstractmethod

from Crypto.Cipher import AES
from Crypto.Hash import SHA256


class CryptoInterface(ABC):
    """
    Интерфейс для криптографических средств, обеспечивающий необходимый функционал работы с YD.
    """

    @abstractmethod
    def __init__(self, key: bytes) -> None:
        pass

    @abstractmethod
    def encrypt_data(self, data: bytes) -> bytes:
        """
        Метод для шифрования блока данных.
        """
        pass

    @abstractmethod
    def decrypt_data(self, data: bytes) -> bytes:
        """
        Метод для дешифрования блока данных.
        """
        pass

    @abstractmethod
    def hash_data(self, data: bytes) -> bytes:
        """
        Метод для хеширования блока данных.
        """
        pass


class CryptodomeAES(CryptoInterface):
    """
    Используем алгоритм симметричной криптографии AES стороннего пакета "pycryptodome".
    """

    def __init__(self, key: bytes) -> None:
        self._AES_key = self.hash_data(key)

    def encrypt_data(self, data: bytes) -> bytes:
        """
        Функция шифрования данных симметричным криптоалгоритмом AES.
        """

        cipher = AES.new(self._AES_key, AES.MODE_EAX)
        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return nonce + tag + ciphertext

    def decrypt_data(self, data: bytes) -> bytes:
        """
        Функция дешифрования данных симметричным криптоалгоритмом AES.
        """

        nonce = data[:16]
        tag = data[16:32]
        ciphertext = data[32:]
        cipher = AES.new(self._AES_key, AES.MODE_EAX, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)

    def hash_data(self, data: bytes) -> bytes:
        """
        Метод для хеширования пакета данных по алгоритму SHA256.
        """

        return SHA256.new(data).digest()
