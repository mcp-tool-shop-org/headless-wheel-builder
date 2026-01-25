# Headless Wheel Builder — GitHub Issues Punch List

One issue per bullet. Each includes acceptance criteria inline.

## P0 — Must-fix

### Issue: Validate python_version support early for DockerIsolation
**Priority:** P0  
**Area:** docker isolation

**Problem:** Docker builds rely on `MANYLINUX_PYTHON_PATHS`. If an unsupported `python_version` is provided, the failure can happen later (KeyError / confusing error).

**Work:**
- Validate `python_version` in `_select_python_path()` (or wherever chosen) and raise `IsolationError` with a clear message listing supported versions.
- Add unit test for unsupported version.

**Acceptance criteria:**
- Unsupported versions raise `IsolationError` with supported versions listed.
- Supported versions work without exceptions.

---

### Issue: Make Docker image selection return canonical full image URLs deterministically
**Priority:** P0  
**Area:** docker isolation

**Problem:** `_select_image()` computes a platform key, but callers should always receive the canonical full URL (from `MANYLINUX_IMAGES`) and it should be stable across runs.

**Work:**
- Ensure `_select_image()` returns `MANYLINUX_IMAGES[platform_key]` when key exists.
- If key missing, raise `IsolationError` with available keys.

**Acceptance criteria:**
- Returned image string matches `quay.io/pypa/...` for known keys.
- Unknown arch/platform combos raise `IsolationError` with helpful message.
- Unit tests cover explicit override, auto default, arch adjustments, and missing key behavior.

---

### Issue: Harden wheel validation against unsafe paths and missing required metadata
**Priority:** P0  
**Area:** security/correctness

**Problem:** Wheel validation protects against path traversal and required files. This must remain locked down.

**Work:**
- Keep `_validate_wheel()` rejecting absolute paths and `..` entries.
- Ensure errors are `BuildError` and include the offending name.
- Add tests for unsafe paths and missing WHEEL/METADATA.

**Acceptance criteria:**
- Unsafe paths raise `BuildError` with the exact offending path included.
- Missing WHEEL or METADATA raises `BuildError` with clear message.
- Tests cover unsafe path and required metadata checks.

---

### Issue: Ensure `clean_output` cannot accidentally delete outside configured output_dir
**Priority:** P0  
**Area:** safety

**Problem:** Cleanup should only remove artifacts in `output_dir`, and only matching intended patterns.

**Work:**
- Confirm cleanup uses `output_dir.glob("*.whl")` and `*.tar.gz` only.
- Add guard: refuse to clean if `output_dir` resolves to root directory or home directory (defensive).

**Acceptance criteria:**
- Cleanup deletes only `*.whl` and `*.tar.gz` inside output_dir.
- Defensive guard prevents cleaning dangerous directories.
- Unit test verifies cleanup deletes expected files and nothing else.

---

## P1 — High leverage

### Issue: Make build output writes atomic to avoid half-written artifacts
**Priority:** P1  
**Area:** build reliability

**Problem:** If a build crashes mid-copy, users can end up with partial wheels.

**Work:**
- Copy artifacts to a temp file in `output_dir`, fsync, then atomic rename.
- Validate wheel after final move.

**Acceptance criteria:**
- Final artifact appears only after successful copy+validate.
- If copy fails, no partial `.whl` remains in output_dir.
- Unit test simulates failure during copy and asserts no partial file remains.

---

### Issue: Standardize structured BuildResult error codes for automation use
**Priority:** P1  
**Area:** API ergonomics

**Problem:** Downstream tools need stable categories.

**Work:**
- Add `error_code` field to `BuildResult` (e.g., `SOURCE_RESOLVE_FAILED`, `ANALYZE_FAILED`, `ISOLATION_FAILED`, `BACKEND_FAILED`, `VALIDATION_FAILED`).
- Populate consistently.

**Acceptance criteria:**
- All failures set `error_code`.
- JSON output includes `error_code`.
- Unit tests verify mapping for at least 3 representative failures.

---

### Issue: Add deterministic build logs with timestamps and phase markers
**Priority:** P1  
**Area:** observability

**Work:**
- Add structured phase markers (resolve/analyze/isolation/build/validate/metadata).
- Include elapsed time per phase.

**Acceptance criteria:**
- Build logs include a phase header for each phase.
- On failure, last phase is clearly indicated.
- Unit test asserts log contains phase markers.

---

## P2 — Maintainability & scale

### Issue: Add CI matrix for Python versions and optional Docker mode
**Priority:** P2  
**Area:** CI

**Work:**
- Test on Python 3.10–3.13.
- Run unit tests only in CI (integration optionally nightly).
- Add a job that runs docker-related unit tests without Docker installed (should not require Docker daemon).

**Acceptance criteria:**
- CI green across matrix.
- Docker unit tests pass even when `docker` executable is absent (no daemon dependency).

---

### Issue: Add golden tests for image selection tables and supported python paths
**Priority:** P2  
**Area:** regression prevention

**Work:**
- Snapshot or explicit tests to ensure `MANYLINUX_IMAGES` and `MANYLINUX_PYTHON_PATHS` include expected keys.
- Prevent accidental removals.

**Acceptance criteria:**
- Unit test fails if expected keys are removed.
- Documentation lists supported python versions and images.

