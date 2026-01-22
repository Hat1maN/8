FROM python:3.11

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install django djangorestframework psycopg2-binary django-cors-headers djangorestframework-simplejwt pillow django-import-export openpyxl tablib[all]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]