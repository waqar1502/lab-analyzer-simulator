# Security policy

This simulator is for isolated development and integration testing. Do not connect it to production systems or use it with protected health information.

Please report security issues privately to the repository maintainers rather than opening a public issue with exploit details. Include the affected version, a minimal reproduction, and the expected/actual behavior.

The default HTTP bind address is `127.0.0.1`. A deployment that binds to a network interface must add network controls, authentication, TLS termination, and access logging appropriate to its environment. The simulator intentionally has no user authentication layer in v0.1.0.
