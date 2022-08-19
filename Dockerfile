#Create ubuntu as base image
FROM python
WORKDIR /api

#Install packages
#RUN ["apt-get", "update", "-y"]
#RUN ["apt-get", "install","vim", "python3", "python3-pip",  "ca-certificates" ,"curl", "gnupg" ,"lsb-release", "git" ,"-y"]
RUN ["pip", "install", "pipenv"]
COPY ./api /api
RUN ["pipenv", "install", "--system", "--deploy","--ignore-pipfile" ]
CMD ["gunicorn", "wsgi:app", "--config", "gunicorn_config.py" ]
ENV PYTHONUNBUFFERED 1

EXPOSE 5002/tcp

