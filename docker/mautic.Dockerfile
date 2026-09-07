# Mautic 7.2.0 Apache, resolved 2026-09-07. Includes Guzzle 7.15.5 with
# upstream's real ~7.15.2 constraint; no Composer aliases or dependency rewrites.
FROM mirror.gcr.io/mautic/mautic@sha256:dea3bb71a5c5bf4c0c7d1764e58a32109898e7b2e6a710f14f50e2a913c03a0f AS sanitized
USER root
ARG SOURCE_DATE_EPOCH
COPY docker/postal-security/debian.sources.list /etc/apt/sources.list
RUN test -n "${SOURCE_DATE_EPOCH}" \
    && rm -f /etc/apt/sources.list.d/* \
    && DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Check-Valid-Until=false update \
    && DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y \
    && DEBIAN_FRONTEND=noninteractive apt-get purge -y nodejs \
    && docker-php-ext-install pcntl \
    && docker-php-source delete \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
        /var/www/html/node_modules /root/.composer /root/.npm \
        /usr/lib/node_modules /tmp/node-compile-cache \
    && rm -f /usr/bin/node /usr/bin/npm /usr/bin/npx /usr/bin/corepack \
        /var/www/html/package-lock.json /var/log/apt/* /var/log/dpkg.log \
        /var/log/alternatives.log /var/cache/ldconfig/aux-cache

WORKDIR /var/www/html
# Verify the exact upstream lock and its installed resolution before any cleanup.
RUN echo '59ec10ac76c91171d4139dad05f70c1817022ce4ca068e9f9243e2189a5da9f4  composer.json' | sha256sum -c - \
    && echo '995c5149fa9cb76c750a32a19b9168aad1db74cc10d39a3aedc96cb1ff7928f9  composer.lock' | sha256sum -c - \
    && COMPOSER_ALLOW_SUPERUSER=1 composer validate --no-check-publish --no-plugins \
    && COMPOSER_ALLOW_SUPERUSER=1 composer check-platform-reqs --no-dev --no-plugins \
    && php -r 'require "vendor/autoload.php"; $lock=json_decode(file_get_contents("composer.lock"),true,512,JSON_THROW_ON_ERROR); if ($lock["aliases"] !== [] || Composer\InstalledVersions::getPrettyVersion("mautic/core-lib") !== "7.2.0" || Composer\InstalledVersions::getPrettyVersion("guzzlehttp/guzzle") !== "7.15.5") {exit(1);}' \
    && php bin/console --version \
    && rm -rf var/cache/* var/tmp/* \
    && rm -rf /root/.composer /tmp/* \
    && mkdir -p var/cache var/tmp /var/lib/klyrow-mautic/config \
    && chown -R root:root /var/www/html \
    && chmod -R go-w /var/www/html \
    && sed -ri 's/Listen 80/Listen 8080/' /etc/apache2/ports.conf \
    && sed -ri 's/\*:80>/*:8080>/' /etc/apache2/sites-available/*.conf \
    && printf '\nServerName localhost\nServerTokens Prod\nServerSignature Off\n' >> /etc/apache2/apache2.conf \
    && printf '\ndisplay_errors=Off\nlog_errors=On\nexpose_php=Off\n' > /usr/local/etc/php/conf.d/klyrow.ini

COPY --chmod=0644 docker/mautic-runtime/local.php /var/www/html/config/local.php
COPY --chmod=0644 docker/mautic-runtime/apache.conf /etc/apache2/conf-enabled/klyrow-media.conf
COPY --chmod=0755 docker/mautic-runtime/runtime.py /usr/local/bin/klyrow-mautic

# Flatten the sanitized filesystem so upstream generated cache/key fixtures and
# removed build tooling cannot be recovered from the candidate's lower layers.
FROM scratch AS mautic-runtime
COPY --from=sanitized / /
ARG SOURCE_COMMIT_SHA
ARG SOURCE_DATE_EPOCH
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PHP_INI_DIR=/usr/local/etc/php \
    APACHE_CONFDIR=/etc/apache2 \
    APACHE_ENVVARS=/etc/apache2/envvars \
    APACHE_DOCUMENT_ROOT=/var/www/html/docroot \
    APACHE_RUN_DIR=/tmp/apache2 \
    APACHE_LOCK_DIR=/tmp/apache2 \
    APACHE_PID_FILE=/tmp/apache2/apache2.pid \
    APACHE_RUN_USER=www-data \
    APACHE_RUN_GROUP=www-data \
    PHP_INI_VALUE_DATE_TIMEZONE=UTC \
    PHP_INI_VALUE_MEMORY_LIMIT=512M \
    PHP_INI_VALUE_UPLOAD_MAX_FILESIZE=32M \
    PHP_INI_VALUE_POST_MAX_FILESIZE=32M \
    PHP_INI_VALUE_MAX_EXECUTION_TIME=300 \
    DOCKER_MAUTIC_ROLE=mautic_web \
    DOCKER_MAUTIC_RUN_MIGRATIONS=false \
    DOCKER_MAUTIC_LOAD_TEST_DATA=false \
    KLYROW_MAUTIC_JOBS_ENABLED=false \
    DEBUG=false
LABEL org.opencontainers.image.source="https://github.com/appolon1908-hue/klyrow.com" \
    org.opencontainers.image.revision="${SOURCE_COMMIT_SHA}" \
    org.opencontainers.image.version="7.2.0-klyrow-candidate"
USER 33:33
WORKDIR /var/www/html
EXPOSE 8080
STOPSIGNAL SIGWINCH
ENTRYPOINT ["/usr/local/bin/klyrow-mautic"]
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 CMD ["/usr/local/bin/klyrow-mautic", "healthcheck"]
