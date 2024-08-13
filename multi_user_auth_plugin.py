import base64
from typing import Optional
from google.cloud import firestore
from proxy.http.proxy import HttpProxyBasePlugin
from proxy.http.parser import HttpParser
from proxy.http.exception import ProxyAuthenticationFailed

class MultiUserAuthPlugin(HttpProxyBasePlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.USERS = {}
        self.firestore_client = firestore.Client()
        self.collection_name = 'users'

    def load_user_from_firestore(self, username: str) -> Optional[str]:
        doc_ref = self.firestore_client.collection(self.collection_name).document(username)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get('password')
        return None

    def cache_user(self, username: str, password: str):
        self.USERS[username] = password

    def get_cached_password(self, username: str) -> Optional[str]:
        return self.USERS.get(username)

    def before_upstream_connection(
        self, request: HttpParser
    ) -> Optional[HttpParser]:
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

    def is_authenticated(self, request: HttpParser) -> bool:
        auth_header = request.headers.get(b'proxy-authorization')
        if auth_header:
            try:
                auth_type, credentials = auth_header[1].split(b' ', 1)
                if auth_type.lower() == b'basic':
                    decoded_credentials = base64.b64decode(credentials).decode('utf-8')
                    username, password = decoded_credentials.split(':', 1)

                    cached_password = self.get_cached_password(username)
                    if cached_password:
                        if cached_password == password:
                            return True
                    else:
                        firestore_password = self.load_user_from_firestore(username)
                        if firestore_password and firestore_password == password:
                            self.cache_user(username, password)
                            return True
            except Exception as e:
                print(f"Ошибка в процессе авторизации: {e}")
        return False
