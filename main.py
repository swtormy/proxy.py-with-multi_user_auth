from proxy import Proxy
import logging
import os
import asyncio

logging.basicConfig(level=logging.DEBUG)

async def run_proxy():
    proxy_params = [
        "--hostname", os.getenv("HOST", "0.0.0.0"),
        "--port", os.getenv("PORT", "8899"),
        "--enable-dashboard",
        "--plugins", "multi_user_auth_plugin.MultiUserAuthPlugin"
    ]

    try:
        with Proxy(proxy_params) as p:
            print(f"Proxy запущен на {p.flags.hostname}:{p.flags.port}")
            try:
                while True:
                    pass
            except KeyboardInterrupt:
                print("Proxy остановлен")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(run_proxy())
