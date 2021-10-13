FROM python:3.9.1

RUN mkdir /app
WORKDIR /app
RUN cd /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

