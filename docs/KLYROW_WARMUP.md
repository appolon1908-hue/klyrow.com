# Klyrow Warm-up

Provider policy carries hourly and daily warm-up limits plus a bounded growth percentage. Effective limits are the minimum of platform rate limits, warm-up limits, tenant quota, and authoritative entitlement. A zero warm-up limit means the corresponding platform limit applies; it does not grant unlimited sending.

Warm-up is tracked per tenant now and is designed to extend to domain, stream, and IP-pool schedules without requiring another IP.
