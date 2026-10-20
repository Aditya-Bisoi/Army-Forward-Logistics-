# Authentication Testing Playbook

1. Log in with `admin@forwardlogistics.demo` / `ControlTower2026!` at `/api/auth/login`.
2. Confirm the response contains the role `admin` and the session cookie is set.
3. Call `/api/auth/me` with the cookie or returned bearer token.
4. Confirm the control tower loads only after authentication.
5. Confirm logout clears the session and returns to the mission access screen.

This prototype uses synthetic data only. It is not an operational command system.