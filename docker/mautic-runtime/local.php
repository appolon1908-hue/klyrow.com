<?php
// The offline bundle is operator-owned configuration, never an application mount.
// Preserve the existing installation identity; credentials come from secret files.
try {
    $parameters = [];
    @require '/var/lib/klyrow-mautic/config/local.php';
    if (!is_array($parameters) || empty($parameters['site_url']) ||
        ($parameters['db_driver'] ?? null) !== 'pdo_mysql') {
        throw new RuntimeException('Invalid installation configuration');
    }
    $readSecret = static function (string $name): string {
        $path = getenv($name . '_FILE');
        if (getenv($name) !== false || !is_string($path) ||
            !preg_match('#^/run/secrets/[A-Za-z0-9][A-Za-z0-9_.-]*$#D', $path) ||
            is_link($path) || !is_file($path)) {
            throw new RuntimeException('Secret file required');
        }
        $handle = @fopen($path, 'rb');
        if ($handle === false) {
            throw new RuntimeException('Secret file unreadable');
        }
        try {
            $value = stream_get_contents($handle, 65537);
        } finally {
            fclose($handle);
        }
        if (!is_string($value) || strlen($value) > 65536) {
            throw new RuntimeException('Invalid secret file');
        }
        $value = preg_replace('/\r?\n\z/', '', $value);
        if ($value === '' || strpbrk($value, "\r\n\0") !== false) {
            throw new RuntimeException('Invalid secret value');
        }
        return $value;
    };
    $parameters['db_password'] = $readSecret('MAUTIC_DB_PASSWORD');
    $parameters['mailer_dsn'] = $readSecret('MAUTIC_MAILER_DSN');
    $parameters['secret_key'] = $readSecret('MAUTIC_SECRET_KEY');
    unset($readSecret);
} catch (Throwable $error) {
    // Never expose values, paths, or the original exception in web/worker logs.
    throw new RuntimeException('Klyrow Mautic configuration is unavailable');
}
