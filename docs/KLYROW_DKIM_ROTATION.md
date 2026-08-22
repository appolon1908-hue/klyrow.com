# Klyrow DKIM Rotation

Rotation generates RSA-2048 material inside the protected DKIM volume. Private PEM files use mode `0600`; APIs return only a protected reference and the public TXT value. A new selector remains `PENDING_DNS` while the prior key stays active.

Activation requires one byte-exact public TXT match. Only then is the new key marked `ACTIVE` and prior active keys marked `RETIRED`. Operators must back up the protected volume and never copy private keys into tickets, logs, evidence, or DNS.
