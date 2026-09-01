FROM ghcr.io/postalserver/postal:3.3.7@sha256:e54b4a7eb106ee15eda5664311c4b9415546d4196f5c4336d23a78d6ce57b819
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
COPY docker/postal-security/Gemfile /opt/postal/app/Gemfile
COPY docker/postal-security/Gemfile.lock /opt/postal/app/Gemfile.lock
RUN bundle config set deployment true \
    && bundle config set without 'development test' \
    && bundle install --jobs 4 --retry 3 \
    && bundle clean --force \
    && rm -rf \
        /usr/local/bundle/gems/{activestorage-7.1.6,activesupport-7.1.6,addressable-2.8.6,bcrypt-3.1.20,concurrent-ruby-1.3.6,faraday-2.9.0,jwt-2.8.1,net-imap-0.5.8,puma-7.0.4,uri-1.0.3,websocket-driver-0.8.0} \
        /usr/local/bundle/extensions/*/*/{bcrypt-3.1.20,puma-7.0.4,websocket-driver-0.8.0} \
        /usr/local/lib/ruby/gems/3.4.0/gems/{erb-4.0.4,net-imap-0.5.8,uri-1.0.3,zlib-3.2.1} \
    && rm -f \
        /usr/local/bundle/specifications/{activestorage-7.1.6,activesupport-7.1.6,addressable-2.8.6,bcrypt-3.1.20,concurrent-ruby-1.3.6,faraday-2.9.0,jwt-2.8.1,net-imap-0.5.8,puma-7.0.4,uri-1.0.3,websocket-driver-0.8.0}.gemspec \
        /usr/local/lib/ruby/gems/3.4.0/cache/net-imap-0.5.8.gem \
        /usr/local/lib/ruby/gems/3.4.0/specifications/net-imap-0.5.8.gemspec \
    && rm -rf /usr/lib/node_modules/npm /usr/lib/node_modules/corepack \
    && rm -f /usr/bin/npm /usr/bin/npx /usr/bin/corepack \
    && rm -f \
        /usr/local/lib/ruby/gems/3.4.0/specifications/default/erb-4.0.4.gemspec \
        /usr/local/lib/ruby/gems/3.4.0/specifications/default/uri-1.0.3.gemspec \
        /usr/local/lib/ruby/gems/3.4.0/specifications/default/zlib-3.2.1.gemspec \
    && find /opt/postal/app/vendor/bundle -type f \
        \( -name gem_make.out -o -name mkmf.log \) -delete \
    && find /opt/postal/app/vendor/bundle -type d -exec chmod 0755 {} + \
    && rm -rf /root/.bundle/cache \
    && bundle exec ruby -e 'expected={"rails"=>"7.2.3.2","jwt"=>"2.10.3","puma"=>"7.2.1","zlib"=>"3.2.3"}; expected.each{|name,version| abort("unexpected #{name}") unless Gem.loaded_specs[name]&.version&.to_s==version}'
RUN mkdir -p /opt/klyrow
COPY apps/postal-provisioner/provisioner.rb /opt/klyrow/provisioner.rb
WORKDIR /opt/postal/app
EXPOSE 9090
CMD ["sh", "-lc", "bundle exec rails runner /opt/klyrow/provisioner.rb"]
