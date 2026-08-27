FROM ghcr.io/postalserver/postal:3.3.7
USER root
RUN mkdir -p /opt/klyrow
COPY apps/postal-provisioner/provisioner.rb /opt/klyrow/provisioner.rb
WORKDIR /opt/postal/app
EXPOSE 9090
CMD ["sh", "-lc", "bundle exec rails runner /opt/klyrow/provisioner.rb"]
