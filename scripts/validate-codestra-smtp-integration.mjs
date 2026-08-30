import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const manifestPath = path.join(root, 'codestra/integration/klyrow-smtp.integration.v1.json');
const providerContractPath = path.join(root, 'codestra/integration/smtp-provider-contract.v1.json');
const openBaoAliasesPath = path.join(root, 'codestra/integration/openbao-secret-aliases.v1.json');
const envPath = path.join(root, 'codestra/integration/runtime.env.example');
const metricsContractPath = path.join(root, 'monitoring/klyrow-smtp-metrics-contract.v1.json');
const targetPath = path.join(root, 'monitoring/prometheus-target.disabled.yml');
const docsPath = path.join(root, 'docs/CODESTRA-SMTP-INTEGRATION-FILES.md');

function fail(message) {
  console.error(`ERROR: ${message}`);
  process.exit(1);
}

function read(file) {
  if (!fs.existsSync(file)) fail(`missing required file: ${path.relative(root, file)}`);
  return fs.readFileSync(file, 'utf8');
}

const manifest = JSON.parse(read(manifestPath));
const providerContract = JSON.parse(read(providerContractPath));
const openBaoAliases = JSON.parse(read(openBaoAliasesPath));
const env = read(envPath);
const metricsContract = JSON.parse(read(metricsContractPath));
const target = read(targetPath);
const docs = read(docsPath);

if (manifest.schemaVersion !== '1.0') fail('manifest schemaVersion must be 1.0');
if (manifest.application !== 'klyrow.com') fail('manifest application must be klyrow.com');
if (manifest.codestraBusiness !== 'klyrow-email') fail('manifest codestraBusiness must be klyrow-email');
if (manifest.status !== 'SMTP_INTEGRATION_FILES_PREPARED_NOT_DEPLOYED') fail('manifest must remain not deployed');
if (manifest.identity?.browserSecretsAllowed !== false) fail('browser secrets must be disallowed');
if (manifest.identity?.smtpCredentialsAreUserPasswords !== false) fail('SMTP credentials must not be user passwords');
if (manifest.gateway?.directProviderWritesAllowed !== false) fail('direct provider writes must be disallowed');
if (manifest.smtp?.approvedRelay !== 'Postal') fail('Postal must remain the approved relay');
if (manifest.smtp?.publicSubmissionEnabledByDefault !== false) fail('public SMTP must be disabled by default');
if (manifest.smtp?.liveDeliveryEnabledByDefault !== false) fail('live delivery must be disabled by default');
if (manifest.observability?.metricsEnabledByDefault !== false) fail('metrics must be disabled by default');
if (manifest.productionGates?.liveEmailDeliveryEnabled !== false) fail('live delivery gate must be false');
if (manifest.productionGates?.publicSmtpEnabled !== false) fail('public SMTP gate must be false');
if (manifest.productionGates?.metricsTargetEnabled !== false) fail('metrics target gate must be false');

if (providerContract.status !== 'PREPARED_NOT_DEPLOYED') fail('provider contract must remain prepared only');
if (providerContract.authority?.runtimeWriteAuthority !== 'Middleware-') fail('Middleware must be runtime write authority');
if (providerContract.authority?.smtpRelay !== 'Postal') fail('Postal must be SMTP relay');
if (providerContract.invariants?.browserMayHoldSmtpSecrets !== false) fail('browser SMTP secrets invariant must be false');
if (providerContract.invariants?.externalProviderWritesBypassMiddleware !== false) fail('provider writes must not bypass Middleware');
if (providerContract.invariants?.liveDeliveryDefault !== false) fail('live delivery default must be false');

for (const command of ['email.message.send.v1', 'email.message.cancel.v1', 'email.domain.verify.v1', 'email.suppression.upsert.v1']) {
  if (!manifest.middleware?.allowedCommands?.includes(command)) fail(`manifest missing command: ${command}`);
  if (!providerContract.commands?.some((entry) => entry.type === command)) fail(`provider contract missing command: ${command}`);
}

if (openBaoAliases.authority !== 'Codestra-OpenBao') fail('OpenBao alias authority mismatch');
if (openBaoAliases.gitMayContainSecretValues !== false) fail('OpenBao aliases must not allow secret values in Git');
for (const alias of openBaoAliases.aliases || []) {
  if (!alias.name?.startsWith('klyrow/') && !alias.name?.startsWith('klyrow-email/')) fail(`OpenBao alias must be namespaced: ${alias.name}`);
  const mount = alias.env || alias.mountedAs || '';
  if (mount !== 'n8n credential store item' && !mount.endsWith('_FILE') && !mount.endsWith('_KEY') && !mount.endsWith('_CERT')) fail(`OpenBao alias must reference a file, key, cert or credential-store mount: ${alias.name}`);
}

if (metricsContract.status !== 'CONTRACT_PREPARED_NOT_SCRAPED') fail('metrics contract must remain not scraped');
if (metricsContract.metricsEnabledByDefault !== false) fail('metrics contract must keep metrics disabled by default');
if (metricsContract.application !== manifest.application) fail('metrics contract application must match manifest');
if (metricsContract.codestraBusiness !== manifest.codestraBusiness) fail('metrics contract business must match manifest');

for (const label of ['codestra_business', 'application', 'service', 'environment', 'server', 'region', 'deployment']) {
  if (!manifest.observability.requiredLabels.includes(label)) fail(`manifest missing required label: ${label}`);
  if (!metricsContract.requiredLabels.includes(label)) fail(`metrics contract missing required label: ${label}`);
  if (!target.includes(label)) fail(`disabled Prometheus target must include label: ${label}`);
}

for (const forbidden of manifest.observability.forbiddenLabels) {
  if (!metricsContract.forbiddenLabels.includes(forbidden)) fail(`metrics contract must forbid label: ${forbidden}`);
  if (!target.includes('labeldrop') || !target.includes(forbidden)) fail(`Prometheus target must drop forbidden label: ${forbidden}`);
}

for (const metric of ['http_requests_total', 'http_request_duration_seconds', 'klyrow_email_outbox_oldest_seconds', 'klyrow_provider_queue_messages', 'klyrow_middleware_command_total', 'klyrow_build_info']) {
  if (!metricsContract.metricFamilies.some((family) => family.name === metric)) fail(`metrics contract missing family: ${metric}`);
}

for (const flag of ['KLYROW_SAFE_MODE=true', 'LIVE_EMAIL_DELIVERY=false', 'EXTERNAL_EMAIL_DELIVERY=false', 'PRODUCTION_PROVIDER_ROUTING=false', 'KLYROW_SECURITY_SMTP_ENABLED=false', 'KLYROW_SECURITY_SMTP_LIVE_ENABLED=false', 'KLYROW_PUBLIC_SMTP_ENABLED=false', 'KLYROW_POSTAL_LIVE_CANARY_ENABLED=false', 'KLYROW_MIDDLEWARE_CANARY_ENABLED=false', 'METRICS_ENABLED=false']) {
  if (!env.includes(flag)) fail(`runtime env template must keep disabled flag: ${flag}`);
}

for (const secret of ['CLIENT_SECRET=', 'TOKEN=', 'PASSWORD=', 'API_KEY=', 'SERVER_KEY=', 'CREDENTIAL=']) {
  if (env.includes(secret) && !env.includes('_FILE=')) fail(`runtime env contains inline secret pattern: ${secret}`);
}

for (const fragment of ['Caddy', 'Kong', 'Middleware', 'Postal', 'OpenBao', 'Activation Gates', 'STARTTLS']) {
  if (!docs.includes(fragment)) fail(`docs missing ${fragment}`);
}

console.log('Codestra Klyrow SMTP integration files validation PASS');
