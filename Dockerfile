
# Imagem oficial do Python
FROM python:3.14-slim

# Evita arquivos .pyc e mantém logs visíveis no GitHub Actions
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Diretório de trabalho
WORKDIR /app

# Instala as dependências Python
COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Cria usuário sem privilégios administrativos
RUN addgroup --system django \
    && adduser --system --ingroup django django \
    && chown -R django:django /app

# Executa a aplicação como usuário não-root
USER django

# Porta utilizada pelo Django/Gunicorn
EXPOSE 8000

# Inicializa a aplicação Django
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
