FROM mirror.gcr.io/mautic/mautic@sha256:373a3de08dfce296e31fe0b7caf269594c43020454628f445c169990b9af4d5e

USER root
COPY docker/postal-security/debian.sources.list /etc/apt/sources.list
RUN rm -f /etc/apt/sources.list.d/* \
    && DEBIAN_FRONTEND=noninteractive apt-get \
        -o Acquire::Check-Valid-Until=false update \
    && DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && rm -f \
        /var/log/apt/* \
        /var/log/dpkg.log \
        /var/log/alternatives.log \
        /var/cache/ldconfig/aux-cache

WORKDIR /var/www/html
COPY docker/mautic-security/composer-security.patch /tmp/composer-security.patch
RUN patch --batch --forward --fuzz=0 -p0 < /tmp/composer-security.patch \
    && rm -f /tmp/composer-security.patch \
    && composer install \
        --no-dev \
        --no-interaction \
        --no-progress \
        --prefer-dist \
    && DEBIAN_FRONTEND=noninteractive apt-get purge -y nodejs \
    && rm -rf \
        node_modules \
        /root/.composer/cache \
        /root/.npm \
        /tmp/node-compile-cache \
        /usr/lib/node_modules/npm \
        /usr/lib/node_modules/corepack \
    && rm -f /usr/bin/node /usr/bin/npm /usr/bin/npx /usr/bin/corepack \
    && rm -f package-lock.json \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && rm -f \
        /var/log/apt/* \
        /var/log/dpkg.log \
        /var/log/alternatives.log \
        /var/cache/ldconfig/aux-cache \
    && composer audit --no-dev --abandoned=ignore \
    && composer validate --no-check-publish \
    && php bin/console --version

WORKDIR /var/www/html/docroot
