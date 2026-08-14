ARG BUILD_FROM
FROM ${BUILD_FROM}

ARG BUILD_VERSION=dev

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
COPY config.yaml /app/addon-config.yaml
# BUILD_VERSION is injected by HA Supervisor; including it here busts the
# cached frontend layer on every add-on version bump.
RUN echo "${BUILD_VERSION}" > .build-version \
  && VITE_APP_VERSION="${BUILD_VERSION}" npm run build

WORKDIR /app
COPY backend/ /app/backend/
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
