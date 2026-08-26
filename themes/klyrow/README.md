# Klyrow Keycloak themes

This directory contains presentation-only login and email themes. It does not change Keycloak source or realm configuration.

- `login` extends the supported `keycloak.v2` parent and supplies responsive Klyrow styles plus English and Spanish messages for login, registration, identity-provider continuation/linking, verification, password recovery, required actions, TOTP, expiry, error and logout surfaces.
- `email` extends `base` and brands verification, password-reset and required-action email in HTML and plain text.

Install the directory as `/opt/keycloak/themes/klyrow` in a reviewed infrastructure branch or deployment. Select `klyrow` as the realm login and email theme only after compatibility testing against the deployed Keycloak version. No deployment or realm mutation is part of Mission 01.
