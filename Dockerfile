# syntax=docker/dockerfile:1

FROM python:3
WORKDIR /usr/src/app
COPY data.json ./
COPY requirements.txt ./
COPY private.key ./
RUN chmod 600 private.key
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV ENVIRONMENT=docker
CMD [ "python", "./src/main.py"]