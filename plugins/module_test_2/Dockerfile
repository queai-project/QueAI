FROM python:3.11-slim

WORKDIR /code

# Instalamos dependencias directas para no crear requirements.txt en esta prueba
RUN pip install --no-cache-dir fastapi uvicorn

# Copiamos el código
COPY ./app /code/app

# Copiamos los archivos del frontend "compilado"
COPY ./frontend_dist /code/frontend_dist

# Comando de ejecución
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]