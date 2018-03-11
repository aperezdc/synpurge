FROM python:3-alpine

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["synpurge"]
