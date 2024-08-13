import base64
from typing import Optional
from google.cloud import firestore
from proxy.http.proxy import HttpProxyBasePlugin
from proxy.http.parser import HttpParser
from google.oauth2 import service_account
import logging

class MultiUserAuthPlugin(HttpProxyBasePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.USERS = {}
        self.credentials = service_account.Credentials.from_service_account_file("creds.json")
        self.firestore_client = firestore.Client(credentials=self.credentials)
        self.collection_name = 'users'
        self.logger = logging.getLogger(__name__)
        log = "MultiUserAuthPlugin проинициализирован"
        self.logger.info(log)

    def load_users_from_firestore(self) -> dict:
        log = "Загрузка всех пользователей из Firestore"
        self.logger.info(log)

        users_ref = self.firestore_client.collection(self.collection_name)
        docs = users_ref.stream()

        users = {}
        for doc in docs:
            user_data = doc.to_dict()
            username = user_data.get('username')
            password = user_data.get('password')
            if username and password:
                users[username] = password
                log = f"Загружен пользователь {username}"
                self.logger.info(log)

        return users

    def cache_user(self, username: str, password: str):
        log = f"Кэширование пользователя {username}"
        self.logger.info(log)
        self.USERS[username] = password

    def get_cached_password(self, username: str) -> Optional[str]:
        log = f"Получение пароля из кэша для пользователя {username}"
        self.logger.info(log)
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

                    cached_password = self.get_cached_password(username)
                    if cached_password:
                        if cached_password == password:
                            log = f"Авторизация пользователя {username} успешна через кэш"
                            self.logger.info(log)
                            return True
                    else:
                        # Загружаем всех пользователей из Firestore
                        all_users = self.load_users_from_firestore()

                        if username in all_users and all_users[username] == password:
                            self.cache_user(username, password)
                            log = f"Авторизация пользователя {username} успешна через Firestore"
                            self.logger.info(log)
                            return True
                log = f"Неправильные учетные данные для пользователя {username}"
                self.logger.info(log)
            except Exception as e:
                log = f"Ошибка в процессе авторизации: {e}"
                self.logger.error(log)
        return False
