# Narrow backend-only Klyrow provisioning bridge loaded through Postal's own Rails models.
require "socket"
require "json"
require "digest"
require "uri"

HOST = ENV.fetch("KLYROW_POSTAL_PROVISIONER_BIND", "0.0.0.0")
PORT = Integer(ENV.fetch("KLYROW_POSTAL_PROVISIONER_PORT", "9090"))
TOKEN_FILE = ENV.fetch("KLYROW_POSTAL_PROVISIONER_TOKEN_FILE", "/run/secrets/klyrow_postal_provisioner_token")
TOKEN = File.read(TOKEN_FILE).strip
raise "provisioner token too short" if TOKEN.bytesize < 32
INBOUND_LOCAL_PARTS = %w[appolon billing support].freeze
INBOUND_ENDPOINT_URL = ENV.fetch("KLYROW_POSTAL_INBOUND_URL", "http://gateway:8000/v1/webhooks/postal-inbound")
inbound_uri = URI.parse(INBOUND_ENDPOINT_URL)
raise "invalid inbound endpoint URL" unless inbound_uri.scheme == "http" && inbound_uri.host == "gateway" &&
  inbound_uri.port == 8000 && inbound_uri.path == "/v1/webhooks/postal-inbound" && inbound_uri.query.nil?


def reply(client, status, body)
  payload = JSON.generate(body)
  text = {200=>"OK",201=>"Created",400=>"Bad Request",401=>"Unauthorized",404=>"Not Found",405=>"Method Not Allowed",422=>"Unprocessable Entity",500=>"Internal Server Error"}.fetch(status,"Error")
  client.write("HTTP/1.1 #{status} #{text}\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nContent-Length: #{payload.bytesize}\r\nConnection: close\r\n\r\n#{payload}")
end


def secure_token?(supplied)
  return false if supplied.nil?
  candidate = supplied.sub(/\ABearer\s+/i, "")
  ActiveSupport::SecurityUtils.secure_compare(Digest::SHA256.hexdigest(candidate), Digest::SHA256.hexdigest(TOKEN))
rescue StandardError
  false
end


def provisioned_server_for_tenant!(tenant_id)
  organization = Organization.find_by!(name: "Klyrow #{tenant_id}")
  organization.servers.find_by!(name: "Klyrow #{tenant_id}")
end


def provision(payload)
  tenant_id = String(payload.fetch("tenant_id"))
  raise ArgumentError, "invalid tenant_id" unless tenant_id.match?(/\A[a-zA-Z0-9-]{1,80}\z/)
  tenant_name = String(payload["tenant_name"] || "Workspace").gsub(/[\r\n]/, " ")[0, 120]
  send_limit = [[Integer(payload["send_limit"] || 1000), 100].max, 10_000].min
  admin = User.find_by!(email_address: ENV.fetch("KLYROW_ADMIN_EMAIL"))
  org_name = "Klyrow #{tenant_id}"
  server_name = "Klyrow #{tenant_id}"
  result = nil
  ActiveRecord::Base.transaction do
    organization = Organization.find_or_create_by!(name: org_name) { |row| row.owner = admin }
    OrganizationUser.find_or_create_by!(organization: organization, user: admin) { |row| row.admin = true; row.all_servers = true }
    server = organization.servers.find_or_create_by!(name: server_name) do |row|
      row.mode = "Development"
      row.send_limit = send_limit
    end
    raise "existing Postal server is not in Development mode" unless server.mode.to_s.casecmp("Development").zero?
    credential = server.credentials.find_or_create_by!(name: "Klyrow Gateway", type: "API")
    result = {
      "tenant_id" => tenant_id,
      "tenant_name" => tenant_name,
      "organization_id" => organization.id.to_s,
      "organization_permalink" => (organization.respond_to?(:permalink) ? organization.permalink : organization.id).to_s,
      "server_id" => server.id.to_s,
      "server_permalink" => (server.respond_to?(:permalink) ? server.permalink : server.id).to_s,
      "mode" => "Development",
      "api_key" => credential.key.to_s
    }
  end
  result
end


def reconcile_inbound(payload)
  tenant_id = String(payload.fetch("tenant_id"))
  raise ArgumentError, "invalid tenant_id" unless tenant_id.match?(/\A[a-zA-Z0-9-]{1,80}\z/)
  domains = Array(payload.fetch("domains")).map { |value| String(value).downcase }.uniq.sort
  raise ArgumentError, "invalid domain count" if domains.empty? || domains.length > 100
  raise ArgumentError, "invalid domain" unless domains.all? { |value| value.match?(/\A[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\z/) }
  reconciled = []
  ActiveRecord::Base.transaction do
    server = provisioned_server_for_tenant!(tenant_id)
    domains.each do |name|
      domain = server.domains.find_by!(name: name)
      raise "Postal domain is not verified" if domain.verified_at.nil?
      raise "Postal inbound is disabled" unless domain.incoming
      raise "Postal domain tenant ownership mismatch" unless domain.owner == server
      endpoint = server.http_endpoints.find_or_initialize_by(name: "Klyrow signed inbound adapter")
      endpoint.assign_attributes(
        url: INBOUND_ENDPOINT_URL, encoding: "BodyAsJSON", format: "RawMessage",
        strip_replies: false, include_attachments: true, timeout: 15,
      )
      endpoint.save!
      INBOUND_LOCAL_PARTS.each do |local_part|
        route = domain.routes.find_or_initialize_by(name: local_part)
        route.server = server
        route.endpoint = endpoint
        route.mode = "Endpoint"
        route.spam_mode = "Mark"
        route.save!
      end
      reconciled << {"domain" => name, "server_id" => server.id.to_s, "routes" => INBOUND_LOCAL_PARTS}
    end
  end
  {"tenant_id" => tenant_id, "endpoint" => "Klyrow signed inbound adapter", "domains" => reconciled}
end


def reconcile_outbound(payload)
  tenant_id = String(payload.fetch("tenant_id"))
  raise ArgumentError, "invalid tenant_id" unless tenant_id.match?(/\A[a-zA-Z0-9-]{1,80}\z/)
  domains = Array(payload.fetch("domains")).map { |value| String(value).downcase }.uniq.sort
  raise ArgumentError, "invalid domain count" if domains.empty? || domains.length > 100
  raise ArgumentError, "invalid domain" unless domains.all? { |value| value.match?(/\A[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\z/) }
  reconciled = []
  ActiveRecord::Base.transaction do
    server = provisioned_server_for_tenant!(tenant_id)
    domains.each do |name|
      domain = server.domains.find_by!(name: name)
      raise "Postal domain is not verified" if domain.verified_at.nil?
      raise "Postal domain tenant ownership mismatch" unless domain.owner == server
      raise "Postal outbound server is not live" unless server.mode.to_s.casecmp("Live").zero?
      credential = server.credentials.find_or_create_by!(
        name: "Klyrow Webmail #{tenant_id}", type: "API"
      )
      reconciled << {
        "domain" => name,
        "server_id" => server.id.to_s,
        "server_permalink" => (server.respond_to?(:permalink) ? server.permalink : server.id).to_s,
        "mode" => "Live",
        "api_key" => credential.key.to_s,
      }
    end
  end
  {"tenant_id" => tenant_id, "domains" => reconciled}
end

server = TCPServer.new(HOST, PORT)
STDOUT.sync = true
puts({event:"postal_provisioner_started", bind:HOST, port:PORT}.to_json)
loop do
  client = server.accept
  begin
    request_line = client.gets&.strip
    raise ArgumentError, "empty request" unless request_line
    method, path, _version = request_line.split(" ", 3)
    headers = {}
    while (line = client.gets)
      line = line.strip
      break if line.empty?
      key, value = line.split(":", 2)
      headers[key.to_s.downcase] = value.to_s.strip
    end
    if method == "GET" && path == "/healthz"
      reply(client, 200, {status:"ok", mode:"Development-only"})
      next
    end
    unless method == "POST" && ["/v1/provision", "/v1/reconcile-inbound", "/v1/reconcile-outbound"].include?(path)
      reply(client, 404, {error:"not_found"})
      next
    end
    unless secure_token?(headers["authorization"])
      reply(client, 401, {error:"unauthorized"})
      next
    end
    length = Integer(headers.fetch("content-length", "0"))
    raise ArgumentError, "invalid body size" if length <= 0 || length > 16_384
    payload = JSON.parse(client.read(length))
    result = case path
             when "/v1/provision" then provision(payload)
             when "/v1/reconcile-inbound" then reconcile_inbound(payload)
             else reconcile_outbound(payload)
             end
    reply(client, 201, result)
  rescue JSON::ParserError, ArgumentError, KeyError => e
    reply(client, 422, {error:e.class.name})
  rescue StandardError => e
    warn({event:"postal_provisioning_failed", error:e.class.name}.to_json)
    reply(client, 500, {error:"provisioning_failed"})
  ensure
    client.close rescue nil
  end
end
