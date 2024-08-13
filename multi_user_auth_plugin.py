import base64
from typing import Optional
from google.cloud import firestore
from proxy.http.proxy import HttpProxyBasePlugin
from proxy.http.parser import HttpParser
from google.oauth2 import service_account


class MultiUserAuthPlugin(HttpProxyBasePlugin):
    USERS = {}
    credentials = service_account.Credentials.from_service_account_file("creds.json")
    firestore_client = firestore.Client(credentials=credentials)


    def load_users_from_firestore(self) -> dict:
        log = "[multi_user]: Загрузка всех пользователей из Firestore"
        print(log)

        users_ref = self.firestore_client.collection('users')
        docs = users_ref.stream()

        users = {}
        for doc in docs:
            user_data = doc.to_dict()
            username = user_data.get('username')
            password = user_data.get('password')
            if username and password:
                users[username] = password
                log = f"[multi_user]: Загружен пользователь {username}"
                print(log)

        return users

    def cache_user(self, username: str, password: str):
        log = f"[multi_user]: Кэширование пользователя {username}"
        print(log)
        self.USERS[username] = password

    def get_cached_password(self, username: str) -> Optional[str]:
        log = f"[multi_user]: Получение пароля из кэша для пользователя {username}"
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
                    log = f"[multi_user]: Попытка авторизации пользователя {username}"
                    print(log)

                    cached_password = self.get_cached_password(username)
                    if cached_password:
                        if cached_password == password:
                            log = f"[multi_user]: Авторизация пользователя {username} успешна через кэш"
                            print(log)
                            return True
                    else:
                        all_users = self.load_users_from_firestore()

                        if username in all_users and all_users[username] == password:
                            self.cache_user(username, password)
                            log = f"[multi_user]: Авторизация пользователя {username} успешна через Firestore"
                            print(log)
                            return True
                log = f"[multi_user]: Неправильные учетные данные для пользователя {username}"
                print(log)
            except Exception as e:
                log = f"[multi_user]: Ошибка в процессе авторизации: {e}"
                print(log)
        return False
