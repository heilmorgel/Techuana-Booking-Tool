ARG BUILD_FROM
FROM ${BUILD_FROM}

ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
ENV DEV_MODE=0

WORKDIR /app

RUN apk add --no-cache nodejs npm

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip3 install --no-cache-dir -r /app/backend/requirements.txt

COPY frontend/package.json /app/frontend/
WORKDIR /app/frontend
RUN npm install

COPY frontend/ /app/frontend/
RUN npm run build

WORKDIR /app
COPY backend/ /app/backend/
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
