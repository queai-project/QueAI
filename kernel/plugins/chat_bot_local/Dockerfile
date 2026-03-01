FROM python:3.11-slim

WORKDIR /code

# Copiamos el código
COPY ./app /code/app
COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Copiamos los archivos del frontend "compilado"
COPY ./frontend_dist /code/frontend_dist

# Comando de ejecución
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]