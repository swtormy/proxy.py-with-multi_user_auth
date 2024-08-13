FROM python:3.12-slim

RUN pip install proxy.py

COPY . /app
COPY creds.json /app/creds.json
WORKDIR /app

ENV HOST=0.0.0.0
ENV PORT=8899
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/creds.json"

CMD ["python", "-u", "main.py", "--hostname", "$HOST", "--port", "$PORT", "--enable-dashboard", "--plugins", "multi_user_auth_plugin.MultiUserAuthPlugin"]
