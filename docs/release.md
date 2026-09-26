# Release checklist

- Update `pyproject.toml`, `CHANGELOG.md`, and the Docker image version/tag.
- Run unit, contract, integration, and API tests.
- Validate that fixtures contain only synthetic data.
- Build `linux/amd64` and `linux/arm64` images in CI.
- Publish only from a protected version tag to the intended GitHub Container Registry namespace.
- Record the immutable image digest and generated build attestation.
- Smoke-test `/healthz`, `/readyz`, the fixture flow, and one approved live-host flow.
- Report any unimplemented protocol or scenario rather than implying support.
