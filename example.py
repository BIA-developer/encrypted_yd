"""Модуль - демонстрация работы с пакетом "crypto_yd"."""

import getpass  # Для ручного ввода пароля пользователем

from encrypted_yd.encrypted_yd import EncryptedYandexDisk

if __name__ == '__main__':
    # Путь приложения на YD (в терминологии YD)
    app_remote_base_path: str = '/Приложения/demo/'

    # Если мы хотим, чтобы пользователь ввел пароль вручную:
    print('Введите пароль:')
    password = getpass.getpass()
    
    # Токен для доступа к YD в зашифрованном виде (укажите свой).
    encrypted_token = b'c\xce98B\x89\xe29|/\x8b\x9c\xed\x80\xc0\xfc)\xf7\xd9sa\r\x86\xb5\xee\xc8rq\x1b\x9e\xe3s W\xbcrI\xfa\x1ee/\xf2\xe6\xbb#]}\x88\xfb\xec\xc2\xa8\xeak\xc0\x0e\x03[\x8c\xdf~\xda%\xd1\xca\xe0\xcfP\xfa'

    # Создаем экземпляр класса для работы с YD
    eyd = EncryptedYandexDisk(app_remote_base_path, encrypted_token, password)

    # Шифруем и отправляем файлы и директории на YD
    eyd.send_files_and_dirs('d:/test/', app_remote_base_path)

    # Скачиваем на локальный диск и расшифровываем файлы и директории
    eyd.receive_files_and_dirs('d:/test_recieve/', app_remote_base_path)

    print('Готово')
