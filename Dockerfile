FROM python:3.12-slim

COPY req.txt /app/req.txt
RUN pip install -r /app/req.txt

COPY . /app
COPY creds.json /app/creds.json
WORKDIR /app

ENV HOST=0.0.0.0
ENV PORT=8899
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/creds.json"

CMD ["python", "-u", "main.py", "--hostname", "$HOST", "--port", "$PORT", "--enable-dashboard", "--plugins", "multi_user_auth_plugin.MultiUserAuthPlugin"]