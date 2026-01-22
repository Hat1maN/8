FROM python:3.11

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /app

# Создайте requirements.txt если нет
# django==4.2.0
# djangorestframework==3.14.0
# psycopg2-binary==2.9.7
# django-cors-headers==4.2.0
# djangorestframework-simplejwt==5.3.0
# pillow==10.1.0
# django-import-export==3.3.0
# openpyxl==3.1.2
# python-dotenv==1.0.0

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]