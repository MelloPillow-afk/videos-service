# Neon Auth identity and Neon production PostgreSQL

Clients sign in through Neon Auth and send its access token to the videos service as an Authorization bearer token. The videos service validates identity and enforces video permissions; sign-in and account management belong to Neon Auth. Production application data is stored in Neon PostgreSQL.

This reuses the application's chosen identity system and database provider. The production database connection and inbound token validation are separate responsibilities.

Administrator status is managed in Neon Auth. After authenticating a request that requires administrator permission, the videos service looks up the user's current role and requires administrator access. Role changes therefore apply on the next administrative request, without waiting for an existing token to expire. Anonymous viewer requests require no role lookup. The exact Neon Auth role lookup interface remains an implementation detail to verify.

Accepted during the design interview on 2026-10-16.
