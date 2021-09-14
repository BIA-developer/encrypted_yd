"""Модуль - демонстрация работы с пакетом "crypto_yd"."""

import getpass  # Для ручного ввода пароля пользователем

from encrypted_yd.encrypted_yd import EncryptedYandexDisk

if __name__ == '__main__':
    # Путь приложения на YD (в терминологии API YD)
    app_remote_base_path: str = '/Приложения/demo/'

    # Если мы хотим, чтобы пользователь ввел пароль вручную:
    # print('Введите пароль:')
    # password = getpass.getpass()
    # Для демонстрационных целей, пароль хранится в открытом виде (при реальном использовании так делать не нужно)
    password = 'ТестовыйПароль'

    # Для демонстрации создан токен "AQAAAABBnepFAAdOwRtowb-H_EO2gEk0DA3_IHs". Ниже он представлен в зашифрованном
    # виде - так его можно безопасно хранить прямо в файле
    encrypted_token = b's\xf5\xac\xce98B\x89\xe29|/\x8b\x9c\xed\x80\xc0\xfc)\xf7\xd9sa\r\x86\xb5\xee\xc8rq\x1b\x9e\xe3s W\xbcrI\xfa\x1ee/\xf2\xe6\xbb#]}\x88\xfb\xec\xc2\xa8\xeak\xc0\x0e\x03[\x8c\xdf~\xda%\xd1\xca\xe0\xcfP\xfa'

    # Создаем экземпляр класса для работы с YD
    eyd = EncryptedYandexDisk(app_remote_base_path, encrypted_token, password)

    # Шифруем и отправляем файлы и директории на YD
    eyd.send_files_and_dirs('d:/test/', app_remote_base_path)

    # Скачиваем на локальный диск и расшифровываем файлы и директории
    eyd.receive_files_and_dirs('d:/test_recieve/', app_remote_base_path)

    # Получаем перечень ресурсов на YD, расположенных в корневой папке приложения:
    dict_of_remote_files_and_dirs = eyd.list_files_and_dirs(app_remote_base_path)
    # Перечень представляет собой словарь, состоящий из двух словарей. Первый словарь 'uuids' в качестве ключей
    # содержит имена ресурсов на YD (если ресурсы были отправлены на YD с помощью пакета encrypted_yd, то их
    # имена будут в формате uuid4), в качестве значений - кортежи вида ('исходное имя ресурса', 'размер',
    # 'тип ресурса (dir или file)'). Второй словарь 'names' в качестве  ключей содержит исходные имена ресурсов,
    # а в качестве значений - имена этих же ресурсов на YD (теоретически последних может быть несколько, поэтому
    # они помещены во множество (set), однако пакет crypto_yd при отправке файлов или директорий не создает
    # ненужных копий на YD).

    # Теперь удаляем все файлы из корневой директории:
    for uuid in dict_of_remote_files_and_dirs['uuids']:
        eyd.remove(f'{app_remote_base_path}{uuid}')
    # Параметр 'permanently', неявно передаваемый в метод 'remove', по умолчанию равен True - удаляем файлы и
    # директории, находящиеся на YD, навсегда, без помещения их в корзину. Чтобы удалить файлы и директории через
    # корзину, используйте:
    # eyd.remove(app_remote_base_path+res_name_in_uuid_format, permanently=False))

    print('Готово')
