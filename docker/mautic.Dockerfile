FROM mirror.gcr.io/mautic/mautic@sha256:373a3de08dfce296e31fe0b7caf269594c43020454628f445c169990b9af4d5e AS patched

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
    && php bin/console --version \
    && find /var/www/html/var/tmp -mindepth 1 -delete \
    && test -z "$(find /var/www/html/var/tmp -mindepth 1 -print -quit)"

# Repack the sanitized filesystem into one final layer. A deletion in a normal
# derived layer would leave the upstream generated Twig cache, including
# example private-key material, recoverable from image history.
FROM scratch AS runtime
COPY --from=patched / /

ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PHPIZE_DEPS="autoconf dpkg-dev file g++ gcc libc-dev make pkg-config re2c" \
    PHP_INI_DIR=/usr/local/etc/php \
    APACHE_CONFDIR=/etc/apache2 \
    APACHE_ENVVARS=/etc/apache2/envvars \
    PHP_CFLAGS="-fstack-protector-strong -fpic -fpie -O2 -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64" \
    PHP_CPPFLAGS="-fstack-protector-strong -fpic -fpie -O2 -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64" \
    PHP_LDFLAGS="-Wl,-O1 -pie" \
    GPG_KEYS="1198C0117593497A5EC5C199286AF1F9897469DC C28D937575603EB4ABB725861C0779DC5C0A9DE4 AFD8691FDAEDF03BDF6E460563F15A9B715376CA" \
    PHP_VERSION=8.3.32 \
    PHP_URL=https://www.php.net/distributions/php-8.3.32.tar.xz \
    PHP_ASC_URL=https://www.php.net/distributions/php-8.3.32.tar.xz.asc \
    PHP_SHA256=8698ec1f9402fa5e5e872ae3d0916b62f5f27503c1fbfc9cc3521e113355ea92 \
    PHP_INI_VALUE_DATE_TIMEZONE=UTC \
    PHP_INI_VALUE_MEMORY_LIMIT=512M \
    PHP_INI_VALUE_UPLOAD_MAX_FILESIZE=512M \
    PHP_INI_VALUE_POST_MAX_FILESIZE=512M \
    PHP_INI_VALUE_MAX_EXECUTION_TIME=300 \
    DOCKER_MAUTIC_WORKERS_CONSUME_EMAIL=2 \
    DOCKER_MAUTIC_WORKERS_CONSUME_HIT=2 \
    DOCKER_MAUTIC_WORKERS_CONSUME_FAILED=2 \
    DOCKER_MAUTIC_ROLE=mautic_web \
    DOCKER_MAUTIC_RUN_MIGRATIONS=false \
    DOCKER_MAUTIC_LOAD_TEST_DATA=false \
    DEBUG=false \
    FLAVOUR=apache \
    APACHE_DOCUMENT_ROOT=/var/www/html/docroot

LABEL maintainer="Mautic core team <>" vendor="Mautic"
VOLUME ["/var/www/html/config", "/var/www/html/docroot/media/files", "/var/www/html/docroot/media/images", "/var/www/html/var/logs"]
EXPOSE 80
STOPSIGNAL SIGWINCH
WORKDIR /var/www/html/docroot
ENTRYPOINT ["/entrypoint.sh"]
