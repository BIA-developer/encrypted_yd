"""Модуль с описанием основного класса "EncryptedYandexDisk" пакета "encrypted_yd"."""

import os
import sys
from uuid import uuid4
from typing import Union, Any

from loguru import logger

from .connector import *
from .cryptography import *

logger.remove()
logger.add(sys.stderr, level="DEBUG")
logger.add('logger.log', format='{time} {level} {message}', level='INFO', rotation='10 MB', compression='zip')


class EncryptedYandexDisk:
    """
    Класс для хранения файлов на YD в зашифрованном виде.

    Содержимое файлов перед отправкой на YD шифруются. Имена файлов и/или директорий преобразуются в произвольные
    названия, получаемые с помощью uuid4(), при этом исходные имена сохраняются в специальные структуры,
    ассоциированные, соответственно, с файлами и директориями на YD (архитектура YD предусматривает возможность
    прикрепления к пользовательскому файлу или директории дополнительной пользовательской информации, хранимой
    в специальной структуре). При скачивании на локальный диск содержимое фалов, их имена, а также имена директорий
    восстанавливаются (преобразуются к исходному виду).

    """

    def __init__(self
                 , app_base_path: str
                 , encrypted_token: bytes
                 , password: str
                 , connector: ConnectorInterface = ConnectorYaDisk
                 , crypto: CryptoInterface = CryptodomeAES
                 # Ниже указываем названия полей в прикрепляемой к файлу/директории структуре на YD, в которых
                 # хранятся в зашифрованном виде исходные имена файлов/директорий, а также их размер. Такие
                 # "неговорящие" названия полей, заданные по умолчанию, выбраны специально, чтобы третьим лицам
                 # было сложнее понять, что в них хранится.
                 , field_name_for_path: str = 'my1'
                 , field_name_for_len: str = 'my2'
                 ) -> None:

        # Валидируем значение аргумента app_base_path
        if not isinstance(app_base_path, str):
            error_str = f'Аргумент "app_base_path" должен быть <class \'str\'>, а не {type(app_base_path)}'
            logger.error(error_str)
            raise TypeError(error_str)
        if not app_base_path.startswith('/Приложения'):
            error_str = f'Значение аргумента "app_base_path" должно начинаться с "/Приложения"'
            logger.error(error_str)
            raise ValueError(error_str)
        self._app_base_path = app_base_path.rstrip('/')

        self._field_name_for_path = field_name_for_path
        self._field_name_for_len = field_name_for_len

        # Создаем экземпляр класса, поддерживающий CryptoInterface, для получения доступа к криптографическим функциям
        self._crypto = crypto(password.encode('utf-8'))

        # Пробуем расшифровать токен
        try:
            self._token = self._crypto.decrypt_data(encrypted_token).decode('utf-8')
        except ValueError:
            logger.error("Внимание: ошибака расшифрования токена! Возможно Вы ввели неверный пароль!")
            raise ValueError
        else:
            self._yd = connector(token=self._token)

    def _prepare_remote_path(self, path: str) -> str:
        """
        Функция преобразования пути на YD к единому формату.
        """

        # Заменяем обратные слэши на прямые
        path = path.replace('\\', '/')
        # Добавляем базовый путь приложения, если он не содержится в path
        if not path.startswith(self._app_base_path):
            return os.path.join(self._app_base_path, path).replace('\\', '/')
        else:
            return path.rstrip('/')

    def _prepare_properties(self, path: str, file_or_dir_len: Union[int, str]) -> Dict:
        """
        Функция подготовки словаря свойств, который прикрепляется к файлу/директории на YD (в соответствии с API YD).

        В словарь свойств включается зашифрованное имя исходного файла/директории, его/ее размер. Название полей берется
        из "self._field_name_for_path" и "self._field_name_for_len", соответственно. Эти названия имеет смысл делать
        "неговорящими" для того, чтобы третьи лица не могли легко определить их содержимое.
        """

        properties = {
            self._field_name_for_path: self._crypto.encrypt_data(path.encode('utf-8')).hex(),
            self._field_name_for_len: self._crypto.encrypt_data(str(file_or_dir_len).encode('utf-8')).hex()
        }
        return properties

    def send_files_and_dirs(self, local_path: str, remote_dir_path: str) -> None:
        """
        Функция рекурсивной отправки файлов и директорий на YD.
        """

        local_path = local_path.replace('\\', '/').rstrip('/')
        remote_dir_path = self._prepare_remote_path(remote_dir_path)

        if self._yd.patch(remote_dir_path, properties={})['type'] != 'dir':
            error_str = 'Ошибка: Вы указали неверное имя каталога на ЯндексДиске.'
            logger.error(error_str)
            raise ValueError(error_str)

        # Создаем структуру со свойствами файла/директории, которая будет храниться на YD (в соответствии с API YD):
        # в поле "self._field_name_for_path" будет храниться исходное имя файла/директории в зашифрованном виде;
        # в поле "self._field_name_for_len" будет храниться размер файла/директории в зашифрованном виде.
        properties = self._prepare_properties(os.path.basename(local_path), os.path.getsize(local_path))

        # Отправляем директорию
        if os.path.isdir(local_path):
            # Создаем словарь соответствий путей локальных директорий их путям на YD
            paths_dict = dict()
            paths_dict[local_path] = remote_dir_path

            for local_root, dirs, files in os.walk(local_path):
                # Сразу преобразуем local_root к необходимому виду
                local_root = local_root.replace('\\', '/')

                # Получаем список файлов и каталогов на YD для конкретной директории
                list_files_and_dirs = self.list_files_and_dirs(paths_dict[local_root])

                for d in dirs:
                    # Для каждой директории проверяем, нет ли ее уже на YD (с измененным именем)
                    # Если нет, то создаем соответствующую директорию с измененным именем
                    if d not in list_files_and_dirs['names']:
                        logger.debug(f'Директории "{d}" нет на YD, она будет создана с измененным именем.')

                        # Подготавливаем структуру свойств для данной директории
                        properties = self._prepare_properties(d, os.path.getsize(os.path.join(local_root, d)))

                        # Формируем имя для данной директории, под которым она будет храниться на YD
                        new_dir_name = str(uuid4())

                        # Формируем полное имя директории на YD с учетом ее нового имени
                        remote_root = paths_dict[local_root] + '/' + new_dir_name
                        # Сохраняем в словарь соответствий локальных и удаленных путей полученный remote_root
                        paths_dict[local_root + '/' + d] = remote_root

                        # Создаем директорию на YD с новым именем
                        self._yd.mkdir(remote_root)
                        # Прикрепляем к ней структуру со свойствами (описана выше)
                        self._yd.patch(remote_root, properties)
                    else:
                        logger.debug(f'Директория "{d}" уже существует на YD, она не будет создана повторно.')
                        # Получаем путь к директории на YD с ее измененным именем.
                        # Используем итератор, т. к. нужно достать значение из множества, не удаляя его в множестве.
                        dir_path_in_yd = paths_dict[local_root] + '/' + next(iter(list_files_and_dirs['names'][d]))
                        paths_dict[local_root + '/' + d] = dir_path_in_yd

                for f in files:
                    # Для каждого файла проверяем, нет ли его уже на YD (с измененным именем)
                    # Если нет, то отправляем (рекурсивно) его на YD сизмененным именем
                    if f in list_files_and_dirs['names']:
                        logger.debug(f'Файл "{f}" уже есть на ЯндексДиске... пропускаем.')
                    else:
                        self.send_files_and_dirs(local_root + '/' + f, paths_dict[local_root])
        # Отправляем файл
        else:
            remote_files = self.list_files_and_dirs(remote_dir_path)
            if os.path.basename(local_path) in remote_files['names']:
                logger.debug(f'Файл "{os.path.basename(local_path)}" уже есть на ЯндексДиске... пропускаем.')
            else:
                # Открываем файл локально
                with open(local_path, "rb") as f:
                    # Формируем для него имя, под которым он будет храниться на YD
                    new_file_name = str(uuid4())
                    # Создаем шифрованную версию исходного файла с new_file_name
                    with open(new_file_name, mode='wb') as fw:
                        fw.write(self._crypto.encrypt_data(f.read()))

                    # Формируем для файла полный путь на YD
                    remote_path = self._prepare_remote_path(remote_dir_path + '/' + new_file_name)
                    logger.debug(f'Отправляем файл "{local_path}" (измененное имя "{new_file_name}") на YD')
                    # Отправляем файл на YD
                    self._yd.upload(new_file_name, remote_path)
                    # Прикрепляем к нему структуру со свойствами (описана выше)
                    self._yd.patch(remote_path, properties=properties)
                    # Удаляем локальную шифрованную версию файла
                    os.remove(new_file_name)

    def list_files_and_dirs(self, remote_path: str) -> Dict[str, Dict]:
        """
        Функция получения списка файлов и директорий с YD.
        """

        remote_path = self._prepare_remote_path(remote_path)
        # Получаем структуру со свойствами файлов/директорий для указанного пути на YD (в соответствии с API YD):
        properties = self._yd.listdir(remote_path)

        # Создаем словарь словарей для хранения описаний файлов/директорий в удобном для использования виде
        out_dict: Dict[str, Dict] = dict()
        # Ниже словарь, в котором ключ - имя файла/директории на YD (измененное). Значение - кортеж из 3-х элементов:
        # 1. исходное имя файла/директории; 2. размер файла/директории; 3. тип (файл или директория)
        # Напримеер, по измененному имени файла можем узнать исходное.
        out_dict['uuids'] = dict()
        # Ниже словарь, в котором ключ - исходное имя файла. Значение - множество измененных имен для конкретно данного
        # файла. Такая ситуация возможна, поскольку каждый раз отправляя один и тот же файл или директорию на YD, мы
        # формируем для него новое измененное имя. В данном коде эта ситуация проверяется и обрабатывается, но в случае,
        # если различные версии одного и того же файла записаны на YD сторонней программой, то эта ситуация тоже будет
        # учтена.
        # Например, по исходному имени, можем определить измененное (наличие записи в данном словаре указывает на то,
        # что на YD имеется файл с таким же зашифрованным именем, как и в локальной директории.
        out_dict['names'] = dict()

        for _ in properties:
            try:
                # Получаем исходный путь для объекта на YD (исходное имя файла или директории на локальном диске)
                obj_name = self._crypto.decrypt_data(
                    bytearray.fromhex(_['custom_properties'][self._field_name_for_path])).decode()
                # Получаем исходный размер файла или директории
                obj_len = self._crypto.decrypt_data(
                    bytearray.fromhex(_['custom_properties'][self._field_name_for_len])).decode()
                # Получаем тип объекта на YD (определяем, является объект файлом или директорией)
                obj_type = _['type']
                out_dict['uuids'][_['name']] = (obj_name, obj_len, obj_type)
                out_dict['names'].setdefault(obj_name, set()).add(_['name'])
            except Exception as e:
                # Поскольку базовый путь может не содержать пользовательских зашифрованных данных в ассоциированной
                # с ним структуре, то возможно исключение, которое мы игнорируем в таком случае.
                if remote_path != self._app_base_path:
                    logger.error(f'Ошибка "{e}" с файлом {_["file"]}')
        return out_dict

    def receive_files_and_dirs(self, local_dir_path: str, remote_path: str) -> None:
        """
        Функция рекурсивного скачивания файлов и директорий с YD.
        """

        remote_path = self._prepare_remote_path(remote_path)
        local_dir_path = local_dir_path.replace('/', os.path.sep)
        if not os.path.isdir(local_dir_path) or not os.path.exists(local_dir_path):
            error_str = f'Ошибка: входной каталог "{local_dir_path}" недоступен или не существует.'
            logger.error(error_str)
            raise ValueError(error_str)

        # Получаем структуру со свойствами файла/директории с YD (в соответствии с API YD)
        properties = self._yd.patch(self._prepare_remote_path(remote_path), properties={})

        # Скачиваем директорию
        if properties['type'] == 'dir':
            # Получаем список файлов и директорий, находящихся в директории remote_path
            list_files_and_dirs = self.list_files_and_dirs(remote_path)

            # Проходим по полученному списку и отдельно обрабатываем файлы и директории
            for _ in list_files_and_dirs['names']:
                # Получаем параметр "тип" (может быть файл или директория)
                # Если тип - директория, - то обрабатываем как директорию
                if list_files_and_dirs['uuids'][next(iter(list_files_and_dirs['names'][_]))][2] == 'dir':
                    # Создаем локально директорию с восстановленным исходным именем
                    logger.debug(f'Скачиваем директорию "{_}"')
                    os.makedirs(os.path.join(local_dir_path, _), exist_ok=True)
                    # Рекурсивно скачиваем содержимое текущей директории
                    self.receive_files_and_dirs(
                        os.path.join(local_dir_path, _),
                        os.path.join(remote_path, next(iter(list_files_and_dirs['names'][_])))
                    )
                # Иначе обрабатываем как файл (рекурсивно).
                else:
                    self.receive_files_and_dirs(
                        local_dir_path,
                        remote_path + '/' + next(iter(list_files_and_dirs['names'][_]))
                    )

        # Скачиваем файл
        else:
            # Достаем исходное имя файла из прикрепленной к нему структуры на YD (в соответствии с API YD)
            # Оно хранится в зашифрованном виде в словаре "custom_properties" с ключом "self._field_name_for_path"
            obj_name = self._crypto.decrypt_data(
                bytearray.fromhex(properties['custom_properties'][self._field_name_for_path])
            )
            # Преобразуем из байтового в строковый вид
            obj_name = obj_name.decode()

            # Достаем исходный размер файла из прикрепленной к нему структуры на YD (в соответствии с API YD)
            # Он хранится в зашифрованном виде в словаре "custom_properties" с ключом "self._field_name_for_len"
            # Пока не используется
            obj_len = self._crypto.decrypt_data(
                bytearray.fromhex(properties['custom_properties'][self._field_name_for_len])
            )
            obj_len = obj_len.decode()

            # Получаем имя файла в виде, хранимом на YD
            name = properties['name']
            logger.debug(f'Скачиваем файл "{os.path.join(local_dir_path, obj_name)}"')
            # Скачиваем файл "как есть"
            self._yd.download(self._prepare_remote_path(remote_path), os.path.join(local_dir_path, name))
            # Читаем содержимое файла в переменную data
            with open(os.path.join(local_dir_path, name), mode='rb') as f:
                data = f.read()
            # Удаляем скачанный файл
            os.remove(os.path.join(local_dir_path, name))
            # Дешифруем содержимое скачанного файла
            data = self._crypto.decrypt_data(data)
            # Сохраняем полученный результат в файл с его исходным именем
            with open(os.path.join(local_dir_path, obj_name), mode='wb') as f:
                f.write(data)

    def remove(self, remote_path: str, permanently: bool = True) -> None:
        self._yd.remove(remote_path, permanently)
