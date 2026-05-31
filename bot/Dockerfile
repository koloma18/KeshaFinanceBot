FROM python:3.12-slim

WORKDIR /app

COPY bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ .

# Debug: проверить что переменные окружения доступны
RUN echo 'import os; print("BOT_TOKEN:", bool(os.getenv("BOT_TOKEN")))' > /app/check_env.py

CMD python3 -c "import os; print('BOT_TOKEN set:', bool(os.getenv('BOT_TOKEN'))); print('BOT_TOKEN len:', len(os.getenv('BOT_TOKEN', '')))" && python3 main.py
