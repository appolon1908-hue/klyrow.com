# Narrow backend-only Klyrow provisioning bridge loaded through Postal's own Rails models.
require "socket"
require "json"
require "digest"

HOST = ENV.fetch("KLYROW_POSTAL_PROVISIONER_BIND", "0.0.0.0")
PORT = Integer(ENV.fetch("KLYROW_POSTAL_PROVISIONER_PORT", "9090"))
TOKEN_FILE = ENV.fetch("KLYROW_POSTAL_PROVISIONER_TOKEN_FILE", "/run/secrets/klyrow_postal_provisioner_token")
TOKEN = File.read(TOKEN_FILE).strip
raise "provisioner token too short" if TOKEN.bytesize < 32


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
    unless method == "POST" && path == "/v1/provision"
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
    reply(client, 201, provision(payload))
  rescue JSON::ParserError, ArgumentError, KeyError => e
    reply(client, 422, {error:e.class.name})
  rescue StandardError => e
    warn({event:"postal_provisioning_failed", error:e.class.name}.to_json)
    reply(client, 500, {error:"provisioning_failed"})
  ensure
    client.close rescue nil
  end
end
