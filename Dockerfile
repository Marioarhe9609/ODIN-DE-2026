FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-build matplotlib font cache (takes ~60s, saves 4+ min on first request)
RUN python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; fig, ax = plt.subplots(); plt.close(fig); print('Matplotlib cache built')"

COPY agent/ agent/
COPY bot/ bot/
COPY ingestion/ ingestion/

ENV PORT=8080

CMD ["python", "bot/telegram_bot.py"]
