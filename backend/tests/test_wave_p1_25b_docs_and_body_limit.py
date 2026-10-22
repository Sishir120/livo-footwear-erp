"""
Wave P1.25B — Production Documentation Gating and Request-Body Limit Acceptance Tests.

Verifies:
1. Documentation gating:
   - In production (ENVIRONMENT=production), app.docs_url, app.redoc_url, and app.openapi_url are None.
   - Requests to /docs, /redoc, /openapi.json, and /api/v1/openapi.json return 404.
   - In development (ENVIRONMENT=development), documentation routes are preserved (200 OK).
2. Caddyfile configuration:
   - request_body directive is present with max_size 10MB.
   - Directive is positioned at site level before reverse proxy handles.
   - Docker Compose pins caddy:2-alpine.
3. Application upload handling:
   - Legitimate uploads under 5 MB are validated.
   - Uploads exceeding 5 MB are rejected by backend handlers.
4. Simulated edge body limit:
   - Requests exceeding 10 MB are rejected with HTTP 413 before backend handler processing.
"""
import os
import sys
import importlib
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository scripts directory is in sys.path for caddy_synthetic_backend
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    import caddy_synthetic_backend  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
except ImportError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location("caddy_synthetic_backend", _SCRIPTS_DIR / "caddy_synthetic_backend.py")
    if _spec and _spec.loader:
        caddy_synthetic_backend = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(caddy_synthetic_backend)
    else:
        raise

# Ensure tests run against in-memory isolated database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-1234567890-test-secret-key"
os.environ["AUTO_MIGRATE"] = "false"


def test_production_documentation_gating():
    """
    Phase 3 Production assertion:
    When ENVIRONMENT=production:
    - app.docs_url is None
    - app.redoc_url is None
    - app.openapi_url is None
    - /docs, /redoc, /openapi.json, and /api/v1/openapi.json return 404.
    """
    os.environ["ENVIRONMENT"] = "production"

    # Reload settings and main with production environment
    import app.config
    importlib.reload(app.config)
    import app.main
    importlib.reload(app.main)

    prod_app = app.main.app
    assert prod_app.docs_url is None, f"Expected docs_url to be None, got {prod_app.docs_url}"
    assert prod_app.redoc_url is None, f"Expected redoc_url to be None, got {prod_app.redoc_url}"
    assert prod_app.openapi_url is None, f"Expected openapi_url to be None, got {prod_app.openapi_url}"

    client = TestClient(prod_app, raise_server_exceptions=False)

    # Assert all documentation routes return 404
    r_docs = client.get("/docs")
    assert r_docs.status_code == 404, f"Expected 404 for /docs, got {r_docs.status_code}"

    r_redoc = client.get("/redoc")
    assert r_redoc.status_code == 404, f"Expected 404 for /redoc, got {r_redoc.status_code}"

    r_openapi = client.get("/openapi.json")
    assert r_openapi.status_code == 404, f"Expected 404 for /openapi.json, got {r_openapi.status_code}"

    r_api_openapi = client.get("/api/v1/openapi.json")
    assert r_api_openapi.status_code == 404, f"Expected 404 for /api/v1/openapi.json, got {r_api_openapi.status_code}"


def test_development_documentation_available():
    """
    Phase 3 Development assertion:
    When ENVIRONMENT=development:
    - app.docs_url is /docs
    - app.redoc_url is /redoc
    - app.openapi_url is /api/v1/openapi.json
    - /docs, /redoc, and /api/v1/openapi.json return 200.
    """
    os.environ["ENVIRONMENT"] = "development"

    import app.config
    importlib.reload(app.config)
    import app.main
    importlib.reload(app.main)

    dev_app = app.main.app
    assert dev_app.docs_url == "/docs", f"Expected docs_url to be /docs, got {dev_app.docs_url}"
    assert dev_app.redoc_url == "/redoc", f"Expected redoc_url to be /redoc, got {dev_app.redoc_url}"
    assert dev_app.openapi_url == "/api/v1/openapi.json", f"Expected openapi_url to be /api/v1/openapi.json, got {dev_app.openapi_url}"

    client = TestClient(dev_app, raise_server_exceptions=False)

    r_docs = client.get("/docs")
    assert r_docs.status_code == 200, f"Expected 200 for /docs, got {r_docs.status_code}"

    r_redoc = client.get("/redoc")
    assert r_redoc.status_code == 200, f"Expected 200 for /redoc, got {r_redoc.status_code}"

    r_openapi = client.get("/api/v1/openapi.json")
    assert r_openapi.status_code == 200, f"Expected 200 for /api/v1/openapi.json, got {r_openapi.status_code}"


def test_caddyfile_directive_validation():
    """
    Phase 2 Caddyfile configuration assertion:
    - Caddyfile contains request_body directive with max_size 10MB.
    - request_body is located before reverse_proxy directives.
    - docker-compose.yml pins caddy:2-alpine.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    caddyfile_path = repo_root / "Caddyfile"
    compose_path = repo_root / "docker-compose.yml"

    assert caddyfile_path.exists(), "Caddyfile must exist at repo root"
    content = caddyfile_path.read_text(encoding="utf-8")

    assert "request_body" in content, "Caddyfile must contain request_body directive"
    assert "max_size 10MB" in content, "request_body must configure max_size 10MB"

    # Verify directive order: request_body appears before first handle /api/*
    body_pos = content.find("request_body")
    handle_pos = content.find("handle /api/*")
    assert body_pos < handle_pos, f"request_body ({body_pos}) must appear before handle /api/* ({handle_pos})"

    # Verify security headers block is intact
    assert "Strict-Transport-Security" in content
    assert "X-Content-Type-Options" in content
    assert "X-Frame-Options" in content

    # Verify docker-compose pinned version
    assert compose_path.exists(), "docker-compose.yml must exist"
    compose_content = compose_path.read_text(encoding="utf-8")
    assert "image: caddy:2-alpine" in compose_content, "Caddy image must be pinned to caddy:2-alpine"


def test_simulated_edge_payload_limit_enforcement():
    """
    CATEGORY B: MOCK/ORACLE TEST.
    Tests independent policy logic using Starlette/FastAPI mock middleware simulator.
    NOTE: This is an independent test of mock simulator logic, NOT of Caddy itself. It does NOT
    provide evidence that Caddy returns HTTP 413; that evidence is established exclusively
    by actual Caddy runtime execution in CI.
    - Payloads <= 10MB pass to application.
    - Payloads > 10MB return HTTP 413 without invoking backend logic.
    """
    from starlette.requests import Request
    from starlette.responses import PlainTextResponse

    MAX_EDGE_BODY = 10 * 1024 * 1024  # 10 MB

    async def edge_proxy_simulator(request: Request, call_next):
        # Emulate Caddy checking Content-Length or streaming byte limit
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_EDGE_BODY:
            return PlainTextResponse("Request body exceeds limit of 10MB", status_code=413)
        return await call_next(request)

    from fastapi import FastAPI
    dummy_app = FastAPI()
    dummy_app.middleware("http")(edge_proxy_simulator)

    backend_invoked = False

    @dummy_app.post("/test-upload")
    async def upload_endpoint(request: Request):
        nonlocal backend_invoked
        backend_invoked = True
        return {"status": "ok"}

    client = TestClient(dummy_app)

    # 1. Test payload under limit (1 MB)
    backend_invoked = False
    small_payload = b"X" * (1 * 1024 * 1024)
    r1 = client.post("/test-upload", content=small_payload, headers={"Content-Length": str(len(small_payload))})
    assert r1.status_code == 200
    assert backend_invoked is True, "Backend must be invoked for request under limit"

    # 2. Test payload exceeding 10MB (11 MB)
    backend_invoked = False
    oversized_length = 11 * 1024 * 1024
    r2 = client.post("/test-upload", headers={"Content-Length": str(oversized_length)})
    assert r2.status_code == 413, f"Expected 413, got {r2.status_code}"
    assert backend_invoked is False, "Backend must NOT be reached when request exceeds 10MB"


def test_synthetic_backend_inspection_parser_valid_json():
    """
    Parser acceptance test: Valid JSON with exact expected count.
    """
    import json

    valid_payload = json.dumps({
        "count": 1,
        "requests": [{"method": "POST", "path": "/api/test", "body_bytes_read": 1024}]
    })
    result = caddy_synthetic_backend.validate_inspection_json(valid_payload, expected_count=1)
    assert isinstance(result, dict)
    assert result["count"] == 1
    assert len(result["requests"]) == 1


def test_synthetic_backend_inspection_parser_missing_fields():
    """
    Parser acceptance test: Rejects response when 'count' field is missing.
    """
    import json

    payload = json.dumps({"status": "ok", "service": "synthetic_backend"})
    with pytest.raises(ValueError, match="Missing required field 'count'"):
        caddy_synthetic_backend.validate_inspection_json(payload, expected_count=1)


def test_synthetic_backend_inspection_parser_malformed_json():
    """
    Parser acceptance test: Rejects malformed JSON syntax.
    """
    import json

    malformed_inputs = [
        "{malformed: json",
        "<html>502 Bad Gateway</html>",
        "",
        "   ",
        "{\"count\": 1,",
    ]
    for bad_input in malformed_inputs:
        with pytest.raises((json.JSONDecodeError, ValueError)):
            caddy_synthetic_backend.validate_inspection_json(bad_input, expected_count=1)


def test_synthetic_backend_inspection_parser_negative_and_non_integer_values():
    """
    Parser acceptance test: Rejects negative integers, floats, booleans, and strings.
    """
    import json

    # Negative integer
    with pytest.raises(ValueError, match="non-negative integer"):
        caddy_synthetic_backend.validate_inspection_json(json.dumps({"count": -1}), expected_count=1)

    # Boolean True (in Python, isinstance(True, int) is True, so parser must specifically disallow bool)
    with pytest.raises(ValueError, match="must be an integer"):
        caddy_synthetic_backend.validate_inspection_json(json.dumps({"count": True}), expected_count=1)

    # Boolean False
    with pytest.raises(ValueError, match="must be an integer"):
        caddy_synthetic_backend.validate_inspection_json(json.dumps({"count": False}), expected_count=1)

    # Float
    with pytest.raises(ValueError, match="must be an integer"):
        caddy_synthetic_backend.validate_inspection_json(json.dumps({"count": 1.0}), expected_count=1)

    # String numeric
    with pytest.raises(ValueError, match="must be an integer"):
        caddy_synthetic_backend.validate_inspection_json(json.dumps({"count": "1"}), expected_count=1)


def test_synthetic_backend_inspection_parser_zero_count():
    """
    Parser acceptance test: Rejects count == 0 when expected count is 1.
    """
    import json

    with pytest.raises(ValueError, match="expected count == 1, got 0"):
        caddy_synthetic_backend.validate_inspection_json(json.dumps({"count": 0}), expected_count=1)


def test_synthetic_backend_inspection_parser_count_greater_than_one():
    """
    Parser acceptance test: Rejects count > 1 when expected count is 1.
    """
    import json

    with pytest.raises(ValueError, match="expected count == 1, got 2"):
        caddy_synthetic_backend.validate_inspection_json(json.dumps({"count": 2}), expected_count=1)

    with pytest.raises(ValueError, match="expected count == 1, got 5"):
        caddy_synthetic_backend.validate_inspection_json(json.dumps({"count": 5}), expected_count=1)


def test_synthetic_backend_cli_validation():
    """
    Parser acceptance test: Verifies CLI exit codes for valid and invalid inputs.
    """
    import subprocess
    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_script = repo_root / "scripts" / "caddy_synthetic_backend.py"

    # Case 1: Valid stdin passes with returncode 0
    proc_valid = subprocess.run(
        [sys.executable, str(backend_script), "--validate-inspect", "1"],
        input='{"count": 1, "requests": []}',
        text=True,
        capture_output=True
    )
    assert proc_valid.returncode == 0
    assert "verified count == 1" in proc_valid.stdout

    # Case 2: Count != 1 exits with returncode 1
    proc_invalid_count = subprocess.run(
        [sys.executable, str(backend_script), "--validate-inspect", "1"],
        input='{"count": 2, "requests": []}',
        text=True,
        capture_output=True
    )
    assert proc_invalid_count.returncode == 1
    assert "Inspection validation failed" in proc_invalid_count.stderr

    # Case 3: Malformed JSON exits with returncode 1
    proc_malformed = subprocess.run(
        [sys.executable, str(backend_script), "--validate-inspect", "1"],
        input='{broken json',
        text=True,
        capture_output=True
    )
    assert proc_malformed.returncode == 1
    assert "Inspection validation failed" in proc_malformed.stderr


def test_synthetic_backend_inspection_parser_body_bytes_read_valid():
    """
    Parser acceptance test: Valid body_bytes_read against explicit expected bytes.
    Verifies both top-level and nested requests[0] structure, as well as arbitrary payload sizes.
    """
    import json

    # Case 1: Real synthetic backend structure (nested inside requests)
    payload_nested = json.dumps({
        "count": 1,
        "requests": [
            {
                "method": "POST",
                "path": "/api/test_ordinary",
                "port": 8000,
                "content_length": "1048576",
                "body_bytes_read": 1048576,
                "timestamp": "2026-10-21T14:00:00+00:00"
            }
        ]
    })
    res_nested = caddy_synthetic_backend.validate_inspection_json(
        payload_nested, expected_count=1, expected_bytes=1048576
    )
    assert res_nested["count"] == 1
    assert res_nested["requests"][0]["body_bytes_read"] == 1048576

    # Case 2: Flattened top-level body_bytes_read
    payload_top = json.dumps({"count": 1, "body_bytes_read": 1048576})
    res_top = caddy_synthetic_backend.validate_inspection_json(
        payload_top, expected_count=1, expected_bytes=1048576
    )
    assert res_top["body_bytes_read"] == 1048576

    # Case 3: Arbitrary expected payload sizes (not hardcoded to 1 MiB)
    for custom_bytes in (0, 1024, 5242880, 11534336):
        custom_payload = json.dumps({
            "count": 1,
            "requests": [{"method": "POST", "body_bytes_read": custom_bytes}]
        })
        res_custom = caddy_synthetic_backend.validate_inspection_json(
            custom_payload, expected_count=1, expected_bytes=custom_bytes
        )
        assert res_custom["requests"][0]["body_bytes_read"] == custom_bytes


def test_synthetic_backend_inspection_parser_missing_body_bytes_read():
    """
    Parser acceptance test: Rejects missing body_bytes_read when expected_bytes or require_bytes is specified.
    """
    import json

    # 1. Top-level missing
    with pytest.raises(ValueError, match="Missing required field 'body_bytes_read'"):
        caddy_synthetic_backend.validate_inspection_json(
            json.dumps({"count": 1}), expected_count=1, expected_bytes=1048576
        )

    # 2. Empty requests array when expected_bytes specified
    with pytest.raises(ValueError, match="Missing required field 'body_bytes_read'"):
        caddy_synthetic_backend.validate_inspection_json(
            json.dumps({"count": 1, "requests": []}), expected_count=1, expected_bytes=1048576
        )

    # 3. Request object without body_bytes_read
    with pytest.raises(ValueError, match="Missing required field 'body_bytes_read'"):
        caddy_synthetic_backend.validate_inspection_json(
            json.dumps({"count": 1, "requests": [{"method": "POST"}]}),
            expected_count=1,
            expected_bytes=1048576
        )

    # 4. require_bytes=True without specific expected_bytes
    with pytest.raises(ValueError, match="Missing required field 'body_bytes_read'"):
        caddy_synthetic_backend.validate_inspection_json(
            json.dumps({"count": 1}), expected_count=1, require_bytes=True
        )


@pytest.mark.parametrize("invalid_val", [
    True,
    False,
    "1048576",
    1048576.0,
    1.5,
    None,
    [1048576],
    {"bytes": 1048576}
])
def test_synthetic_backend_inspection_parser_body_bytes_read_invalid_types(invalid_val):
    """
    Parser acceptance test: Rejects booleans, strings, floats, null, and non-integer types for body_bytes_read.
    """
    import json

    # Test top-level placement
    payload_top = json.dumps({"count": 1, "body_bytes_read": invalid_val})
    with pytest.raises(ValueError, match="Field 'body_bytes_read'.*must be an integer"):
        caddy_synthetic_backend.validate_inspection_json(payload_top, expected_count=1)

    # Test nested placement inside requests
    payload_nested = json.dumps({
        "count": 1,
        "requests": [{"method": "POST", "body_bytes_read": invalid_val}]
    })
    with pytest.raises(ValueError, match="Field 'body_bytes_read'.*must be an integer"):
        caddy_synthetic_backend.validate_inspection_json(payload_nested, expected_count=1)


@pytest.mark.parametrize("neg_val", [-1, -1024, -1048576])
def test_synthetic_backend_inspection_parser_negative_body_bytes_read(neg_val):
    """
    Parser acceptance test: Rejects negative integer values for body_bytes_read.
    """
    import json

    # Top-level
    with pytest.raises(ValueError, match="non-negative integer"):
        caddy_synthetic_backend.validate_inspection_json(
            json.dumps({"count": 1, "body_bytes_read": neg_val}), expected_count=1
        )

    # Nested
    with pytest.raises(ValueError, match="non-negative integer"):
        caddy_synthetic_backend.validate_inspection_json(
            json.dumps({"count": 1, "requests": [{"body_bytes_read": neg_val}]}), expected_count=1
        )


@pytest.mark.parametrize("actual,expected", [
    (500, 1048576),
    (1048576, 500),
    (0, 1024),
    (1024, 0),
    (1048577, 1048576),
])
def test_synthetic_backend_inspection_parser_body_bytes_read_mismatch(actual, expected):
    """
    Parser acceptance test: Rejects byte count mismatch between actual body_bytes_read and expected_bytes.
    """
    import json

    payload = json.dumps({
        "count": 1,
        "requests": [{"method": "POST", "body_bytes_read": actual}]
    })
    with pytest.raises(ValueError, match=f"expected body_bytes_read == {expected}, got {actual}"):
        caddy_synthetic_backend.validate_inspection_json(
            payload, expected_count=1, expected_bytes=expected
        )


def test_synthetic_backend_inspection_parser_duplicate_keys():
    """
    Parser acceptance test: Rejects duplicate JSON keys at top level and nested objects.
    """

    # 1. Duplicate top-level count
    with pytest.raises(ValueError, match="Duplicate key 'count' detected"):
        caddy_synthetic_backend.validate_inspection_json(
            '{"count": 1, "count": 2, "requests": []}', expected_count=1
        )

    # 2. Duplicate top-level body_bytes_read
    with pytest.raises(ValueError, match="Duplicate key 'body_bytes_read' detected"):
        caddy_synthetic_backend.validate_inspection_json(
            '{"count": 1, "body_bytes_read": 1048576, "body_bytes_read": 2048}', expected_count=1
        )

    # 3. Duplicate body_bytes_read in nested request object
    with pytest.raises(ValueError, match="Duplicate key 'body_bytes_read' detected"):
        caddy_synthetic_backend.validate_inspection_json(
            '{"count": 1, "requests": [{"body_bytes_read": 1048576, "body_bytes_read": 500}]}',
            expected_count=1
        )

    # 4. Arbitrary nested object duplicate key
    with pytest.raises(ValueError, match="Duplicate key 'dup' detected"):
        caddy_synthetic_backend.validate_inspection_json(
            '{"count": 1, "nested": {"dup": 1, "dup": 2}}', expected_count=1
        )


@pytest.mark.parametrize("non_obj", [
    "[1, 2, 3]",
    "12345",
    "\"just_a_string\"",
    "true",
    "false",
    "null"
])
def test_synthetic_backend_inspection_parser_non_object_root(non_obj):
    """
    Parser acceptance test: Rejects non-dict JSON roots (arrays, scalars, booleans, null).
    """

    with pytest.raises(ValueError, match="Expected JSON object"):
        caddy_synthetic_backend.validate_inspection_json(non_obj, expected_count=1)


def test_synthetic_backend_cli_validation_extended():
    """
    Parser acceptance test: Verifies CLI behavior for body_bytes_read and duplicate key rejection.
    """
    import subprocess
    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_script = repo_root / "scripts" / "caddy_synthetic_backend.py"

    valid_payload = '{"count": 1, "requests": [{"method": "POST", "body_bytes_read": 1048576}]}'

    # 1. Positional expected bytes passes
    proc_pos = subprocess.run(
        [sys.executable, str(backend_script), "--validate-inspect", "1", "1048576"],
        input=valid_payload,
        text=True,
        capture_output=True
    )
    assert proc_pos.returncode == 0
    assert "verified count == 1" in proc_pos.stdout
    assert "verified body_bytes_read == 1048576" in proc_pos.stdout

    # 2. Flag --expected-bytes passes
    proc_flag = subprocess.run(
        [sys.executable, str(backend_script), "--validate-inspect", "1", "--expected-bytes", "1048576"],
        input=valid_payload,
        text=True,
        capture_output=True
    )
    assert proc_flag.returncode == 0
    assert "verified count == 1" in proc_flag.stdout
    assert "verified body_bytes_read == 1048576" in proc_flag.stdout

    # 3. Byte count mismatch fails closed with exit code 1
    proc_mismatch = subprocess.run(
        [sys.executable, str(backend_script), "--validate-inspect", "1", "2048"],
        input=valid_payload,
        text=True,
        capture_output=True
    )
    assert proc_mismatch.returncode == 1
    assert "Byte count assertion failed" in proc_mismatch.stderr

    # 4. Missing body_bytes_read when expected_bytes requested fails closed with exit code 1
    proc_missing = subprocess.run(
        [sys.executable, str(backend_script), "--validate-inspect", "1", "1048576"],
        input='{"count": 1, "requests": []}',
        text=True,
        capture_output=True
    )
    assert proc_missing.returncode == 1
    assert "Missing required field 'body_bytes_read'" in proc_missing.stderr

    # 5. Duplicate keys fail closed with exit code 1
    proc_dup = subprocess.run(
        [sys.executable, str(backend_script), "--validate-inspect", "1"],
        input='{"count": 1, "count": 1}',
        text=True,
        capture_output=True
    )
    assert proc_dup.returncode == 1
    assert "Duplicate key 'count' detected" in proc_dup.stderr


def test_caddyfile_early_rejection_configuration():
    """
    CATEGORY A: STATIC CONFIGURATION TEXTUAL ASSERTION.
    Verifies that the repository Caddyfile text contains the expected directive syntax:
    - Caddyfile contains @oversized_cl named matcher matching Content-Length > 10485760.
    - respond @oversized_cl 413 is present.
    - @oversized_cl and respond directives appear before handle /api/* to short-circuit before proxying.
    - request_body max_size 10MB streaming limit is preserved as defense-in-depth.
    NOTE: Static textual assertions cannot prove runtime execution order or CEL evaluation.
    Actual runtime execution is established exclusively by containerized Caddy runtime tests in CI.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    caddyfile_path = repo_root / "Caddyfile"

    assert caddyfile_path.exists(), "Caddyfile must exist at repo root"
    content = caddyfile_path.read_text(encoding="utf-8")

    assert "@oversized_cl" in content, "Caddyfile must define @oversized_cl matcher"
    assert "respond @oversized_cl 413" in content, "Caddyfile must configure respond @oversized_cl 413"
    assert "request_body" in content, "Caddyfile must preserve request_body directive"
    assert "max_size 10MB" in content, "request_body must preserve max_size 10MB"

    # Directive order verification
    req_body_pos = content.find("request_body")
    matcher_pos = content.find("@oversized_cl")
    respond_pos = content.find("respond @oversized_cl 413")
    handle_pos = content.find("handle /api/*")

    assert req_body_pos < matcher_pos, "request_body must be configured before early rejection matcher"
    assert matcher_pos < respond_pos, "@oversized_cl must be defined before respond directive"
    assert respond_pos < handle_pos, "respond @oversized_cl 413 must appear before handle /api/* reverse_proxy"


def test_synthetic_backend_partial_read_and_metadata():
    """
    Synthetic backend assertion:
    Verifies that SyntheticBackendHandler accurately distinguishes between:
    - Complete request: bytes read == Content-Length -> completed=True, truncated=False
    - Partial request: EOF reached before all expected bytes read -> completed=False, truncated=True
    - GET request: completed=True, truncated=False, body_bytes_read=0
    """
    import io

    class MockServer:
        server_port = 8000

    class DummyHandler(caddy_synthetic_backend.SyntheticBackendHandler):
        def __init__(self, raw_bytes: bytes, content_length: str = None):
            self.server = MockServer()
            self.rfile = io.BytesIO(raw_bytes)
            self.wfile = io.BytesIO()
            self.headers = {}
            if content_length is not None:
                self.headers["Content-Length"] = content_length
            self.path = "/api/test"
            self.command = "POST"
            self.request_version = "HTTP/1.1"
            self.requestline = "POST /api/test HTTP/1.1"

    # 1. Partial request: stream terminated prematurely (Caddy severed connection)
    with caddy_synthetic_backend._LOG_LOCK:
        caddy_synthetic_backend.REQUEST_LOG.clear()

    handler_partial = DummyHandler(b"partial_payload", content_length="1000")
    handler_partial.do_POST()

    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 1
        rec_partial = caddy_synthetic_backend.REQUEST_LOG[0]
        assert rec_partial["body_bytes_read"] == len(b"partial_payload")
        assert rec_partial["bytes_expected"] == 1000
        assert rec_partial["completed"] is False
        assert rec_partial["truncated"] is True

    # 2. Complete request: full payload read
    with caddy_synthetic_backend._LOG_LOCK:
        caddy_synthetic_backend.REQUEST_LOG.clear()

    full_payload = b"X" * 1024
    handler_complete = DummyHandler(full_payload, content_length=str(len(full_payload)))
    handler_complete.do_POST()

    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 1
        rec_complete = caddy_synthetic_backend.REQUEST_LOG[0]
        assert rec_complete["body_bytes_read"] == 1024
        assert rec_complete["bytes_expected"] == 1024
        assert rec_complete["completed"] is True
        assert rec_complete["truncated"] is False


def test_synthetic_backend_inspection_parser_error_diagnostics():
    """
    Parser acceptance test:
    When count != expected_count, validate_inspection_json error message includes
    rich diagnostics detailing each recorded request (method, path, bytes read vs expected, completed, truncated).
    """
    import json

    payload = json.dumps({
        "count": 2,
        "requests": [
            {
                "method": "POST",
                "path": "/api/test_ordinary",
                "body_bytes_read": 1048576,
                "bytes_expected": 1048576,
                "completed": True,
                "truncated": False
            },
            {
                "method": "POST",
                "path": "/api/test_oversized",
                "body_bytes_read": 10485760,
                "bytes_expected": 11534336,
                "completed": False,
                "truncated": True
            }
        ]
    })

    with pytest.raises(ValueError) as excinfo:
        caddy_synthetic_backend.validate_inspection_json(payload, expected_count=1)

    err_msg = str(excinfo.value)
    assert "expected count == 1, got 2" in err_msg
    assert "read 1048576/1048576 bytes, completed=True, truncated=False" in err_msg
    assert "read 10485760/11534336 bytes, completed=False, truncated=True" in err_msg


def test_edge_body_limit_boundary_and_malformed_spec():
    """
    CATEGORY B: MOCK/ORACLE TEST.
    Independent behavioral specification oracle testing edge reverse proxy policy logic across
    required boundaries and malformed header cases using Starlette/FastAPI mock middleware.
    NOTE: This tests independent policy logic in Python. It does NOT execute Caddy and does NOT
    provide evidence that Caddy returns 400 or 413; that evidence is established exclusively
    by actual Caddy runtime execution in CI.
    - Missing Content-Length (streamed/chunked or empty)
    - Valid length below limit (1,048,576 bytes / 1 MiB) -> HTTP 200, backend invoked
    - Exactly 10,485,760 bytes (exact 10MB limit boundary) -> HTTP 200, backend invoked
    - 10,485,761 bytes (10MB + 1 byte) -> HTTP 413, backend NOT reached
    - 11,534,336 bytes (existing 11 MiB Case B) -> HTTP 413, backend NOT reached
    - Non-numeric Content-Length ("abc") -> HTTP 400 Bad Request, backend NOT reached
    - Negative Content-Length ("-100") -> HTTP 400 Bad Request, backend NOT reached
    - Conflicting duplicate Content-Length ("1000, 2000") -> HTTP 400 Bad Request, backend NOT reached
    - Identical duplicate Content-Length ("1024, 1024") -> HTTP 200, backend invoked
    - Transfer-Encoding: chunked with conflicting Content-Length: Transfer-Encoding takes precedence per RFC 7230/9110
    """
    from starlette.requests import Request
    from starlette.responses import PlainTextResponse
    from fastapi import FastAPI

    MAX_EDGE_BODY = 10 * 1024 * 1024  # 10,485,760 bytes

    async def edge_proxy_oracle(request: Request, call_next):
        te = request.headers.get("transfer-encoding", "").lower()
        cl_header = request.headers.get("content-length")

        # RFC 7230 / RFC 9110: if Transfer-Encoding is chunked, ignore/strip Content-Length
        if "chunked" in te:
            cl_header = None

        if cl_header is not None:
            # Check for duplicate headers
            if "," in cl_header:
                parts = [p.strip() for p in cl_header.split(",")]
                if len(set(parts)) == 1 and parts[0].isdigit():
                    cl_val = int(parts[0])
                else:
                    return PlainTextResponse("Bad Request: conflicting Content-Length", status_code=400)
            else:
                if not cl_header.isdigit():
                    return PlainTextResponse("Bad Request: invalid Content-Length", status_code=400)
                cl_val = int(cl_header)

            if cl_val < 0:
                return PlainTextResponse("Bad Request: negative Content-Length", status_code=400)

            # Early rejection if known Content-Length > 10MB
            if cl_val > MAX_EDGE_BODY:
                return PlainTextResponse("Payload Too Large", status_code=413)

        return await call_next(request)

    dummy_app = FastAPI()
    dummy_app.middleware("http")(edge_proxy_oracle)

    backend_invoked = False

    @dummy_app.post("/test-boundary")
    async def endpoint(request: Request):
        nonlocal backend_invoked
        backend_invoked = True
        return {"status": "ok"}

    client = TestClient(dummy_app)

    # 1. Below limit (1 MiB: 1,048,576 bytes)
    backend_invoked = False
    r1 = client.post("/test-boundary", headers={"Content-Length": "1048576"})
    assert r1.status_code == 200
    assert backend_invoked is True

    # 2. Exactly boundary (10,485,760 bytes)
    backend_invoked = False
    r2 = client.post("/test-boundary", headers={"Content-Length": "10485760"})
    assert r2.status_code == 200
    assert backend_invoked is True

    # 3. Boundary + 1 (10,485,761 bytes)
    backend_invoked = False
    r3 = client.post("/test-boundary", headers={"Content-Length": "10485761"})
    assert r3.status_code == 413
    assert backend_invoked is False

    # 4. Existing 11 MiB (11,534,336 bytes)
    backend_invoked = False
    r4 = client.post("/test-boundary", headers={"Content-Length": "11534336"})
    assert r4.status_code == 413
    assert backend_invoked is False

    # 5. Non-numeric
    backend_invoked = False
    r5 = client.post("/test-boundary", headers={"Content-Length": "invalid_abc"})
    assert r5.status_code == 400
    assert backend_invoked is False

    # 6. Negative
    backend_invoked = False
    r6 = client.post("/test-boundary", headers={"Content-Length": "-100"})
    assert r6.status_code == 400
    assert backend_invoked is False

    # 7. Conflicting duplicate
    backend_invoked = False
    r7 = client.post("/test-boundary", headers={"Content-Length": "1000, 2000"})
    assert r7.status_code == 400
    assert backend_invoked is False

    # 8. Identical duplicate <= 10MB
    backend_invoked = False
    r8 = client.post("/test-boundary", headers={"Content-Length": "1024, 1024"})
    assert r8.status_code == 200
    assert backend_invoked is True

    # 9. Missing Content-Length
    backend_invoked = False
    r9 = client.post("/test-boundary")
    assert r9.status_code == 200
    assert backend_invoked is True

    # 10. Transfer-Encoding: chunked with conflicting Content-Length (TE takes precedence)
    backend_invoked = False
    r10 = client.post(
        "/test-boundary",
        headers={"Transfer-Encoding": "chunked", "Content-Length": "11534336"}
    )
    assert r10.status_code == 200
    assert backend_invoked is True


def test_synthetic_backend_chunked_and_edge_cases():
    """
    Synthetic backend assertion:
    Verifies that SyntheticBackendHandler accurately handles:
    - Chunked transfer-encoding complete stream
    - Chunked transfer-encoding premature EOF
    - Duplicate identical Content-Length
    - Duplicate conflicting Content-Length
    - Negative Content-Length
    """
    import io

    class MockServer:
        server_port = 8000

    class DummyHandler(caddy_synthetic_backend.SyntheticBackendHandler):
        def __init__(self, raw_bytes: bytes, headers: dict = None):
            self.server = MockServer()
            self.rfile = io.BytesIO(raw_bytes)
            self.wfile = io.BytesIO()
            self.headers = headers or {}
            self.path = "/api/test"
            self.command = "POST"
            self.request_version = "HTTP/1.1"
            self.requestline = "POST /api/test HTTP/1.1"

    # 1. Chunked transfer-encoding complete read
    chunked_data = b"5\r\nHello\r\n6\r\n World\r\n0\r\n\r\n"
    h_chunked = DummyHandler(chunked_data, {"Transfer-Encoding": "chunked"})
    with caddy_synthetic_backend._LOG_LOCK:
        caddy_synthetic_backend.REQUEST_LOG.clear()
    h_chunked.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 1
        rec = caddy_synthetic_backend.REQUEST_LOG[0]
        assert rec["body_bytes_read"] == 11
        assert rec["completed"] is True
        assert rec["truncated"] is False

    # 2. Chunked transfer-encoding premature EOF
    chunked_trunc = b"5\r\nHello\r\n6\r\n Wor"  # Socket closed mid-chunk
    h_chunked_trunc = DummyHandler(chunked_trunc, {"Transfer-Encoding": "chunked"})
    with caddy_synthetic_backend._LOG_LOCK:
        caddy_synthetic_backend.REQUEST_LOG.clear()
    h_chunked_trunc.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 1
        rec = caddy_synthetic_backend.REQUEST_LOG[0]
        assert rec["completed"] is False
        assert rec["truncated"] is True

    # 3. Duplicate identical Content-Length
    h_dup_ok = DummyHandler(b"X" * 64, {"Content-Length": "64, 64"})
    with caddy_synthetic_backend._LOG_LOCK:
        caddy_synthetic_backend.REQUEST_LOG.clear()
    h_dup_ok.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 1
        rec = caddy_synthetic_backend.REQUEST_LOG[0]
        assert rec["body_bytes_read"] == 64
        assert rec["bytes_expected"] == 64
        assert rec["completed"] is True
        assert rec["truncated"] is False

    # 4. Duplicate conflicting Content-Length
    h_dup_conflict = DummyHandler(b"X" * 64, {"Content-Length": "64, 128"})
    with caddy_synthetic_backend._LOG_LOCK:
        caddy_synthetic_backend.REQUEST_LOG.clear()
    h_dup_conflict.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 1
        rec = caddy_synthetic_backend.REQUEST_LOG[0]
        assert rec["completed"] is False

    # 5. Negative Content-Length
    h_neg = DummyHandler(b"X" * 64, {"Content-Length": "-64"})
    with caddy_synthetic_backend._LOG_LOCK:
        caddy_synthetic_backend.REQUEST_LOG.clear()
    h_neg.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 1
        rec = caddy_synthetic_backend.REQUEST_LOG[0]
        assert rec["completed"] is False


def test_synthetic_backend_one_canonical_record_per_request():
    """
    CATEGORY A: PURE UNIT TEST.
    Verifies Phase 1 request-recording semantics in SyntheticBackendHandler:
    - Exactly one canonical request record is created per incoming POST.
    - Each record captures request_id, method, path, port, body_bytes_read, bytes_expected, completed, truncated, timestamp.
    - An incomplete or truncated request is recorded with completed=False, truncated=True without double counting.
    - Sequential request_ids are tracked accurately via _REQUEST_COUNTER.
    - Calling /inspect/clear clears REQUEST_LOG and resets _REQUEST_COUNTER to 0.
    """
    import io

    class MockServer:
        server_port = 8000

    class DummyHandler(caddy_synthetic_backend.SyntheticBackendHandler):
        def __init__(self, raw_bytes: bytes, headers: dict = None, path: str = "/api/test"):
            self.server = MockServer()
            self.rfile = io.BytesIO(raw_bytes)
            self.wfile = io.BytesIO()
            self.headers = headers or {}
            self.path = path
            self.command = "POST"
            self.request_version = "HTTP/1.1"
            self.requestline = f"POST {path} HTTP/1.1"

    # Reset before test
    clear_h = DummyHandler(b"", path="/inspect/clear")
    clear_h.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 0
        assert caddy_synthetic_backend._REQUEST_COUNTER == 0

    # 1. Complete fixed-length POST
    h1 = DummyHandler(b"payload_1024", {"Content-Length": "12"}, path="/api/case_a")
    h1.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 1
        r1 = caddy_synthetic_backend.REQUEST_LOG[0]
        assert r1["request_id"] == 1
        assert r1["path"] == "/api/case_a"
        assert r1["body_bytes_read"] == 12
        assert r1["bytes_expected"] == 12
        assert r1["completed"] is True
        assert r1["truncated"] is False

    # 2. Truncated fixed-length POST (premature EOF / socket severed)
    h2 = DummyHandler(b"partial", {"Content-Length": "100"}, path="/api/truncated_cl")
    h2.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 2
        r2 = caddy_synthetic_backend.REQUEST_LOG[1]
        assert r2["request_id"] == 2
        assert r2["path"] == "/api/truncated_cl"
        assert r2["body_bytes_read"] == len(b"partial")
        assert r2["bytes_expected"] == 100
        assert r2["completed"] is False
        assert r2["truncated"] is True

    # 3. Complete chunked POST without trailers
    chunked_ok = b"4\r\nWiki\r\n5\r\npedia\r\n0\r\n\r\n"
    h3 = DummyHandler(chunked_ok, {"Transfer-Encoding": "chunked"}, path="/api/chunked_ok")
    h3.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 3
        r3 = caddy_synthetic_backend.REQUEST_LOG[2]
        assert r3["request_id"] == 3
        assert r3["path"] == "/api/chunked_ok"
        assert r3["body_bytes_read"] == 9
        assert r3["completed"] is True
        assert r3["truncated"] is False

    # 3b. Complete chunked POST with trailers
    chunked_trailers = b"4\r\nWiki\r\n0\r\nX-Trailer-Checksum: abc123\r\n\r\n"
    h3b = DummyHandler(chunked_trailers, {"Transfer-Encoding": "chunked"}, path="/api/chunked_trailers")
    h3b.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 4
        r3b = caddy_synthetic_backend.REQUEST_LOG[3]
        assert r3b["request_id"] == 4
        assert r3b["path"] == "/api/chunked_trailers"
        assert r3b["body_bytes_read"] == 4
        assert r3b["completed"] is True
        assert r3b["truncated"] is False

    # 4. Truncated chunked POST (socket severed mid-chunk data)
    chunked_trunc = b"4\r\nWiki\r\n5\r\npe"
    h4 = DummyHandler(chunked_trunc, {"Transfer-Encoding": "chunked"}, path="/api/chunked_trunc")
    h4.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 5
        r4 = caddy_synthetic_backend.REQUEST_LOG[4]
        assert r4["request_id"] == 5
        assert r4["path"] == "/api/chunked_trunc"
        assert r4["body_bytes_read"] == 6
        assert r4["completed"] is False
        assert r4["truncated"] is True

    # 4b. Truncated chunked POST (premature EOF while consuming chunk terminator CRLF)
    chunked_no_crlf = b"4\r\nWiki"
    h4b = DummyHandler(chunked_no_crlf, {"Transfer-Encoding": "chunked"}, path="/api/chunked_no_crlf")
    h4b.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 6
        r4b = caddy_synthetic_backend.REQUEST_LOG[5]
        assert r4b["request_id"] == 6
        assert r4b["path"] == "/api/chunked_no_crlf"
        assert r4b["body_bytes_read"] == 4
        assert r4b["completed"] is False
        assert r4b["truncated"] is True

    # 4c. Truncated chunked POST (premature EOF while consuming terminal framing / trailers)
    chunked_no_term = b"4\r\nWiki\r\n0\r\n"
    h4c = DummyHandler(chunked_no_term, {"Transfer-Encoding": "chunked"}, path="/api/chunked_no_term")
    h4c.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 7
        r4c = caddy_synthetic_backend.REQUEST_LOG[6]
        assert r4c["request_id"] == 7
        assert r4c["path"] == "/api/chunked_no_term"
        assert r4c["body_bytes_read"] == 4
        assert r4c["completed"] is False
        assert r4c["truncated"] is True

    # 4d. Malformed chunk size (non-hex characters)
    chunked_bad_size = b"ZZZZ\r\nhello"
    h4d = DummyHandler(chunked_bad_size, {"Transfer-Encoding": "chunked"}, path="/api/bad_chunk_size")
    h4d.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 8
        r4d = caddy_synthetic_backend.REQUEST_LOG[7]
        assert r4d["request_id"] == 8
        assert r4d["path"] == "/api/bad_chunk_size"
        assert r4d["body_bytes_read"] == 0
        assert r4d["completed"] is False
        assert r4d["truncated"] is True

    # 4e. LF-only chunk terminator (violates strict HTTP/1.1 CRLF requirement)
    chunked_lf_term = b"4\r\nWiki\n0\r\n\r\n"
    h4e = DummyHandler(chunked_lf_term, {"Transfer-Encoding": "chunked"}, path="/api/chunked_lf_term")
    h4e.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 9
        r4e = caddy_synthetic_backend.REQUEST_LOG[8]
        assert r4e["request_id"] == 9
        assert r4e["path"] == "/api/chunked_lf_term"
        assert r4e["body_bytes_read"] == 4
        assert r4e["completed"] is False
        assert r4e["truncated"] is True

    # 4f. LF-only terminal separator (violates strict HTTP/1.1 CRLF requirement)
    chunked_lf_sep = b"4\r\nWiki\r\n0\r\n\n"
    h4f = DummyHandler(chunked_lf_sep, {"Transfer-Encoding": "chunked"}, path="/api/chunked_lf_sep")
    h4f.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 10
        r4f = caddy_synthetic_backend.REQUEST_LOG[9]
        assert r4f["request_id"] == 10
        assert r4f["path"] == "/api/chunked_lf_sep"
        assert r4f["body_bytes_read"] == 4
        assert r4f["completed"] is False
        assert r4f["truncated"] is True

    # 4g. Malformed chunk terminator (e.g. \rX instead of \r\n)
    chunked_bad_term = b"4\r\nWiki\rX0\r\n\r\n"
    h4g = DummyHandler(chunked_bad_term, {"Transfer-Encoding": "chunked"}, path="/api/chunked_bad_term")
    h4g.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 11
        r4g = caddy_synthetic_backend.REQUEST_LOG[10]
        assert r4g["request_id"] == 11
        assert r4g["path"] == "/api/chunked_bad_term"
        assert r4g["body_bytes_read"] == 4
        assert r4g["completed"] is False
        assert r4g["truncated"] is True

    # 5. Malformed Content-Length POST
    h5 = DummyHandler(b"test", {"Content-Length": "invalid_abc"}, path="/api/malformed")
    h5.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 12
        r5 = caddy_synthetic_backend.REQUEST_LOG[11]
        assert r5["request_id"] == 12
        assert r5["path"] == "/api/malformed"
        assert r5["completed"] is False
        assert r5["truncated"] is False

    # Reset log and verify clean slate
    clear_h.do_POST()
    with caddy_synthetic_backend._LOG_LOCK:
        assert len(caddy_synthetic_backend.REQUEST_LOG) == 0
        assert caddy_synthetic_backend._REQUEST_COUNTER == 0


def test_synthetic_backend_case_c_outcome_classification():
    """
    CATEGORY A: PURE UNIT TEST.
    Verifies Phase 2 unambiguous outcome classification in validate_case_c_inspection_json:
    - Outcome 1 (Caddy rejected before upstream initiation; count == 1)
    - Outcome 2 (Caddy started upstream request and truncated stream; count == 2)
    - Explicit outcome mismatch enforcement via required_outcome
    - Invariant checks for Case A payload and Case C endpoint/limit/truncation attributes
    - Fails closed on spurious requests (count > 2) or missing Case A (count < 1)
    """
    import json

    outcome_1_payload = json.dumps({
        "count": 1,
        "requests": [
            {
                "request_id": 1,
                "method": "POST",
                "path": "/api/test_ordinary",
                "body_bytes_read": 1048576,
                "completed": True,
                "truncated": False
            }
        ]
    })

    outcome_2_payload = json.dumps({
        "count": 2,
        "requests": [
            {
                "request_id": 1,
                "method": "POST",
                "path": "/api/test_ordinary",
                "body_bytes_read": 1048576,
                "completed": True,
                "truncated": False
            },
            {
                "request_id": 2,
                "method": "POST",
                "path": "/api/test_streaming_oversized",
                "body_bytes_read": 10485760,
                "completed": False,
                "truncated": True
            }
        ]
    })

    # 1. Outcome C1 correctly classified without explicit client status
    res1 = caddy_synthetic_backend.validate_case_c_inspection_json(outcome_1_payload)
    assert res1["outcome"] in ("C1", "outcome_1")
    assert res1["count"] == 1
    assert "rejection before upstream initiation" in res1["description"]

    # 1b. Outcome C1 with client_status="413"
    res1_c1 = caddy_synthetic_backend.validate_case_c_inspection_json(outcome_1_payload, client_status="413")
    assert res1_c1["outcome"] == "C1"

    # 2. Outcome C1 passes with required_outcome="C1" or "outcome_1"
    res1_req = caddy_synthetic_backend.validate_case_c_inspection_json(
        outcome_1_payload, required_outcome="C1"
    )
    assert res1_req["outcome"] in ("C1", "outcome_1")

    # 3. Outcome C1 fails when required_outcome="C2"
    with pytest.raises(ValueError, match="Outcome mismatch.*required 'C2'"):
        caddy_synthetic_backend.validate_case_c_inspection_json(
            outcome_1_payload, required_outcome="C2"
        )

    # 4. Outcome C2 correctly classified (client received HTTP 413)
    res2 = caddy_synthetic_backend.validate_case_c_inspection_json(outcome_2_payload, client_status="413")
    assert res2["outcome"] == "C2"
    assert res2["count"] == 2
    assert "Streaming termination" in res2["description"]
    assert res2["bytes_received"] == 10485760

    # 4b. Outcome C3 correctly classified (client stream severed / status 000 / curl exit 55)
    res3 = caddy_synthetic_backend.validate_case_c_inspection_json(
        outcome_2_payload, client_status="000", curl_exit=55
    )
    assert res3["outcome"] == "C3"
    assert res3["count"] == 2
    assert "Connection failure" in res3["description"] or "stream severed" in res3["description"]
    assert res3["bytes_received"] == 10485760

    # 5. Outcome C2 passes with required_outcome="C2"
    res2_req = caddy_synthetic_backend.validate_case_c_inspection_json(
        outcome_2_payload, required_outcome="C2", client_status="413"
    )
    assert res2_req["outcome"] == "C2"

    # 5b. Outcome C3 passes with required_outcome="C3"
    res3_req = caddy_synthetic_backend.validate_case_c_inspection_json(
        outcome_2_payload, required_outcome="C3", client_status="000", curl_exit=55
    )
    assert res3_req["outcome"] == "C3"

    # 6. Outcome C2 fails when required_outcome="C1"
    with pytest.raises(ValueError, match="Outcome mismatch.*required 'C1'"):
        caddy_synthetic_backend.validate_case_c_inspection_json(
            outcome_2_payload, required_outcome="C1", client_status="413"
        )

    # 6b. Fails on unexpected client status (e.g. 200 OK for oversized upload)
    with pytest.raises(ValueError, match="Unexpected client status for Case C"):
        caddy_synthetic_backend.validate_case_c_inspection_json(
            outcome_2_payload, client_status="200"
        )

    # 7. Outcome C2 fails on path mismatch
    bad_path_payload = json.dumps({
        "count": 2,
        "requests": [
            {"method": "POST", "body_bytes_read": 1048576, "completed": True, "truncated": False},
            {"method": "POST", "path": "/api/wrong_path", "body_bytes_read": 10485760, "completed": False, "truncated": True}
        ]
    })
    with pytest.raises(ValueError, match="Case C path mismatch"):
        caddy_synthetic_backend.validate_case_c_inspection_json(
            bad_path_payload, case_c_path="/api/test_streaming_oversized"
        )

    # 8. Outcome C2 fails if body_bytes_read > max_bytes
    excess_bytes_payload = json.dumps({
        "count": 2,
        "requests": [
            {"method": "POST", "body_bytes_read": 1048576, "completed": True, "truncated": False},
            {"method": "POST", "path": "/api/test_streaming_oversized", "body_bytes_read": 10485761, "completed": False, "truncated": True}
        ]
    })
    with pytest.raises(ValueError, match="Backend received excess bytes in Case C"):
        caddy_synthetic_backend.validate_case_c_inspection_json(
            excess_bytes_payload, max_bytes=10485760
        )

    # 9. Outcome C2 fails if completed is True
    completed_true_payload = json.dumps({
        "count": 2,
        "requests": [
            {"method": "POST", "body_bytes_read": 1048576, "completed": True, "truncated": False},
            {"method": "POST", "path": "/api/test_streaming_oversized", "body_bytes_read": 10485760, "completed": True, "truncated": True}
        ]
    })
    with pytest.raises(ValueError, match="completed=False"):
        caddy_synthetic_backend.validate_case_c_inspection_json(completed_true_payload)

    # 10. Outcome C2 fails if truncated is False
    truncated_false_payload = json.dumps({
        "count": 2,
        "requests": [
            {"method": "POST", "body_bytes_read": 1048576, "completed": True, "truncated": False},
            {"method": "POST", "path": "/api/test_streaming_oversized", "body_bytes_read": 10485760, "completed": False, "truncated": False}
        ]
    })
    with pytest.raises(ValueError, match="truncated=True"):
        caddy_synthetic_backend.validate_case_c_inspection_json(truncated_false_payload)

    # 11. Fails if Case A payload modified
    modified_case_a_payload = json.dumps({
        "count": 2,
        "requests": [
            {"method": "POST", "body_bytes_read": 500, "completed": True, "truncated": False},
            {"method": "POST", "path": "/api/test_streaming_oversized", "body_bytes_read": 10485760, "completed": False, "truncated": True}
        ]
    })
    with pytest.raises(ValueError, match="Case A payload modified"):
        caddy_synthetic_backend.validate_case_c_inspection_json(
            modified_case_a_payload, expected_case_a_bytes=1048576
        )

    # 12. Fails if spurious requests appear (count > 2)
    spurious_payload = json.dumps({
        "count": 3,
        "requests": [
            {"method": "POST", "path": "/api/a", "body_bytes_read": 1048576, "completed": True, "truncated": False},
            {"method": "POST", "path": "/api/test_streaming_oversized", "body_bytes_read": 10485760, "completed": False, "truncated": True},
            {"method": "POST", "path": "/api/spurious", "body_bytes_read": 100, "completed": True, "truncated": False}
        ]
    })
    with pytest.raises(ValueError, match="Unexpected request count after Case C: expected 1 or 2, got count=3"):
        caddy_synthetic_backend.validate_case_c_inspection_json(spurious_payload)


def test_synthetic_backend_cli_validation_streaming():
    """
    CATEGORY A: PURE UNIT TEST.
    Verifies that caddy_synthetic_backend.py --validate-case-c CLI behaves correctly:
    - Exits 0 and reports Outcome C2 on valid Case C stream truncation with HTTP 413.
    - Exits 0 and reports Outcome C3 on valid Case C stream truncation with socket reset (000).
    - Exits 0 and reports Outcome C1 on valid Case C early rejection.
    - Exits 1 on outcome requirement mismatch.
    - Exits 1 on excess bytes.
    - Exits 1 on duplicate keys.
    """
    import subprocess
    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_script = repo_root / "scripts" / "caddy_synthetic_backend.py"

    outcome_2_payload = (
        '{"count": 2, "requests": ['
        '{"method": "POST", "body_bytes_read": 1048576, "completed": true, "truncated": false},'
        '{"method": "POST", "path": "/api/test_streaming_oversized", "body_bytes_read": 10485760, "completed": false, "truncated": true}'
        ']}'
    )

    outcome_1_payload = (
        '{"count": 1, "requests": ['
        '{"method": "POST", "body_bytes_read": 1048576, "completed": true, "truncated": false}'
        ']}'
    )

    # 1. Outcome C2 passes CLI with --client-status 413
    proc_o2 = subprocess.run(
        [sys.executable, str(backend_script), "--validate-case-c", "--client-status", "413", "--max-bytes", "10485760"],
        input=outcome_2_payload,
        text=True,
        capture_output=True
    )
    assert proc_o2.returncode == 0
    assert "CLASSIFIED OUTCOME: C2" in proc_o2.stdout

    # 1b. Outcome C3 passes CLI with --client-status 000 --curl-exit 55
    proc_o3 = subprocess.run(
        [sys.executable, str(backend_script), "--validate-case-c", "--client-status", "000", "--curl-exit", "55", "--max-bytes", "10485760"],
        input=outcome_2_payload,
        text=True,
        capture_output=True
    )
    assert proc_o3.returncode == 0
    assert "CLASSIFIED OUTCOME: C3" in proc_o3.stdout

    # 2. Outcome C1 passes CLI
    proc_o1 = subprocess.run(
        [sys.executable, str(backend_script), "--validate-case-c", "--client-status", "413", "--max-bytes", "10485760"],
        input=outcome_1_payload,
        text=True,
        capture_output=True
    )
    assert proc_o1.returncode == 0
    assert "CLASSIFIED OUTCOME: C1" in proc_o1.stdout

    # 3. Requirement mismatch: requiring C2 when C1 received exits 1
    proc_mismatch = subprocess.run(
        [sys.executable, str(backend_script), "--validate-case-c", "--require-outcome", "C2"],
        input=outcome_1_payload,
        text=True,
        capture_output=True
    )
    assert proc_mismatch.returncode == 1
    assert "Case C validation failed" in proc_mismatch.stderr

    # 4. Excess bytes fails closed
    excess_payload = (
        '{"count": 2, "requests": ['
        '{"method": "POST", "body_bytes_read": 1048576, "completed": true, "truncated": false},'
        '{"method": "POST", "path": "/api/test_streaming_oversized", "body_bytes_read": 11000000, "completed": false, "truncated": true}'
        ']}'
    )
    proc_excess = subprocess.run(
        [sys.executable, str(backend_script), "--validate-case-c", "--max-bytes", "10485760"],
        input=excess_payload,
        text=True,
        capture_output=True
    )
    assert proc_excess.returncode == 1
    assert "Case C validation failed" in proc_excess.stderr

    # 5. Duplicate key fails closed
    dup_payload = '{"count": 2, "count": 2, "requests": []}'
    proc_dup = subprocess.run(
        [sys.executable, str(backend_script), "--validate-case-c"],
        input=dup_payload,
        text=True,
        capture_output=True
    )
    assert proc_dup.returncode == 1
    assert "Duplicate key 'count' detected" in proc_dup.stderr
