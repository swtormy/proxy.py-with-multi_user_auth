import base64
from typing import Optional
from google.cloud import firestore
from proxy.http.proxy import HttpProxyBasePlugin
from proxy.http.parser import HttpParser

import logging

class MultiUserAuthPlugin(HttpProxyBasePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.USERS = {}
        self.firestore_client = firestore.Client()
        self.collection_name = 'users'
        self.logger = logging.getLogger(__name__)

    def load_user_from_firestore(self, username: str) -> Optional[str]:
        log = f"Загрузка пользователя {username} из Firestore"
        self.logger.info(log)
        print(log)
        doc_ref = self.firestore_client.collection(self.collection_name).document(username)
        doc = doc_ref.get()
        if doc.exists:
            password = doc.to_dict().get('password')
            log = f"Найден пароль для пользователя {username}"
            self.logger.info(log)
            print(log)
            return password
        self.logger.warning(f"Пользователь {username} не найден в Firestore")
        self.logger.info(log)
        print(log)
        return None

    def cache_user(self, username: str, password: str):
        log = f"Кэширование пользователя {username}"
        self.logger.info(log)
        print(log)
        self.USERS[username] = password

    def get_cached_password(self, username: str) -> Optional[str]:
        log = f"Получение пароля из кэша для пользователя {username}"
        self.logger.info(log)
        print(log)
        return self.USERS.get(username)

    def is_authenticated(self, request: HttpParser) -> bool:
        auth_header = request.headers.get(b'proxy-authorization')
        if auth_header:
            try:
                auth_type, credentials = auth_header[1].split(b' ', 1)
                if auth_type.lower() == b'basic':
                    decoded_credentials = base64.b64decode(credentials).decode('utf-8')
                    username, password = decoded_credentials.split(':', 1)
                    log = f"Попытка авторизации пользователя {username}"
                    self.logger.info(log)
                    print(log)

                    cached_password = self.get_cached_password(username)
                    if cached_password:
                        if cached_password == password:
                            log = f"Авторизация пользователя {username} успешна через кэш"
                            self.logger.info(log)
                            print(log)
                            return True
                    else:
                        firestore_password = self.load_user_from_firestore(username)
                        if firestore_password and firestore_password == password:
                            self.cache_user(username, password)
                            log = f"Авторизация пользователя {username} успешна через Firestore"
                            self.logger.info(log)
                            print(log)
                            return True
                log = f"Неправильные учетные данные для пользователя {username}"
                self.logger.info(log)
                print(log)
            except Exception as e:
                log = f"Ошибка в процессе авторизации: {e}"
                self.logger.info(log)
                print(log)
        return False
