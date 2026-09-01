FROM ghcr.io/postalserver/postal:3.3.7@sha256:e54b4a7eb106ee15eda5664311c4b9415546d4196f5c4336d23a78d6ce57b819
USER root
RUN mkdir -p /opt/klyrow
COPY apps/postal-provisioner/provisioner.rb /opt/klyrow/provisioner.rb
WORKDIR /opt/postal/app
EXPOSE 9090
CMD ["sh", "-lc", "bundle exec rails runner /opt/klyrow/provisioner.rb"]
