import base64
from typing import Optional
from google.cloud import firestore
from proxy.http.proxy import HttpProxyBasePlugin
from proxy.http.parser import HttpParser
from proxy.http.exception import ProxyAuthenticationFailed
import logging

GLOBAL_USER_CACHE = {}

class MultiUserAuthPlugin(HttpProxyBasePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.firestore_client = firestore.Client()
        self.collection_name = 'users'
        self.logger = logging.getLogger(__name__)

    def before_upstream_connection(
            self, request: HttpParser
    ) -> Optional[HttpParser]:
        print(request.__dict__)
        if not self.is_authenticated(request):
            raise ProxyAuthenticationFailed()
        return request

    def handle_client_request(
            self, request: HttpParser
    ) -> Optional[HttpParser]:
        return request

    def on_client_data(
            self, raw: memoryview
    ) -> Optional[memoryview]:
        return raw

    def load_user_from_firestore(self, username: str) -> Optional[str]:
        self.logger.info(f"Загрузка пользователя {username} из Firestore")

        # Проверка в глобальном кэше
        if username in GLOBAL_USER_CACHE:
            self.logger.info(f"Пользователь {username} найден в глобальном кэше")
            return GLOBAL_USER_CACHE[username]

        users_ref = self.firestore_client.collection(self.collection_name)
        query = users_ref.where('username', '==', username)
        docs = query.stream()

        for doc in docs:
            user_data = doc.to_dict()
            if user_data.get('username') == username:
                password = user_data.get('password')
                self.logger.info(f"Найден пароль для пользователя {username}")
                GLOBAL_USER_CACHE[username] = password
                return password

        self.logger.warning(f"Пользователь {username} не найден в Firestore")
        return None

    def cache_user(self, username: str, password: str):
        self.logger.info(f"Кэширование пользователя {username}")
        GLOBAL_USER_CACHE[username] = password

    def get_cached_password(self, username: str) -> Optional[str]:
        self.logger.info(f"Получение пароля из кэша для пользователя {username}")
        return GLOBAL_USER_CACHE.get(username)

    def is_authenticated(self, request: HttpParser) -> bool:
        auth_header = request.headers.get(b'proxy-authorization')
        if auth_header:
            try:
                auth_type, credentials = auth_header[1].split(b' ', 1)
                if auth_type.lower() == b'basic':
                    decoded_credentials = base64.b64decode(credentials).decode('utf-8')
                    username, password = decoded_credentials.split(':', 1)
                    self.logger.info(f"Попытка авторизации пользователя {username}")

                    cached_password = self.get_cached_password(username)
                    if cached_password:
                        if cached_password == password:
                            self.logger.info(f"Авторизация пользователя {username} успешна через кэш")
                            return True
                    else:
                        firestore_password = self.load_user_from_firestore(username)
                        if firestore_password and firestore_password == password:
                            self.cache_user(username, password)
                            self.logger.info(f"Авторизация пользователя {username} успешна через Firestore")
                            return True
                self.logger.warning(f"Неправильные учетные данные для пользователя {username}")
            except Exception as e:
                self.logger.error(f"Ошибка в процессе авторизации: {e}")
        return False
