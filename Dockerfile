FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py storage.py parser.py server.py handlers.py ./

RUN touch data.json && chmod 666 data.json

EXPOSE 8080

CMD ["python", "bot.py"]
