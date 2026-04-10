FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Hugging Face corre en el puerto 7860
ENV PORT=7860
EXPOSE 7860

# Asegurar permisos para SQLite en /tmp
RUN chmod 777 /tmp

# Comando de inicio
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
