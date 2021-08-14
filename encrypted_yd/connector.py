"""Модуль для описания коннекторов, работающих с YD.

В настоящее время в качестве коннектора используется класс стороннего модуля "yadisk".
Однако в дальнейшем предполагается использование других модулей, в том числе, самописных.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

import yadisk


class ConnectorInterface(ABC):
    """
    Интерфейс, который должны поддерживать коннекторы для обеспечения необходимого функционала работы с YD.
    """

    @abstractmethod
    def __init__(self, token: str) -> None:
        """
        Метод для инициализации коннектора.
        """
        pass

    @abstractmethod
    def upload(self, local_path: str, remote_path: str) -> None:
        """
        Метод для отправки файла на YD.
        """
        pass

    @abstractmethod
    def download(self, remote_path: str, local_path: str) -> None:
        """
        Метод для скачивания файла с YD на локальный диск.
        """
        pass

    @abstractmethod
    def patch(self, remote_path: str, properties: Dict) -> Optional[Dict]:
        """
        Метод для получения или задания свойств файла или директории c/на YD в специальной структуре.
        """
        pass

    @abstractmethod
    def mkdir(self, remote_path: str) -> None:
        """
        Метод для создания директории на YD.
        """
        pass

    @abstractmethod
    def listdir(self, remote_path: str) -> List[Dict]:
        """
        Метод для получения списка файлов и/или директорий по указанному пути на YD.
        """
        pass


class ConnectorYaDisk(ConnectorInterface):
    """
    Класс, использующий модуль "yadisk" для работы с YD.
    """

    def __init__(self, token: str) -> None:
        self._yd = yadisk.YaDisk(token=token)

    def upload(self, local_path: str, remote_path: str) -> None:
        with open(local_path, mode='rb') as f:
            self._yd.upload(f, remote_path)

    def download(self, remote_path: str, local_path: str) -> None:
        self._yd.download(remote_path, local_path)

    def patch(self, remote_path: str, properties: Dict) -> Optional[Dict]:
        return self._yd.patch(remote_path, properties=properties)

    def mkdir(self, remote_path: str) -> None:
        self._yd.mkdir(remote_path)

    def listdir(self, remote_path: str) -> List[Dict]:
        return list(self._yd.listdir(remote_path))
