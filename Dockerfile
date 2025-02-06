FROM python:3.12-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /django-project

COPY requirements.txt /django-project

COPY /src /django-project/src

RUN pip install -r requirements.txt

WORKDIR /django-project/src

RUN python manage.py makemigrations

RUN python manage.py migrate
