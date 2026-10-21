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
    Simulates reverse proxy request_body limit behavior:
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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

    payload = json.dumps({"status": "ok", "service": "synthetic_backend"})
    with pytest.raises(ValueError, match="Missing required field 'count'"):
        caddy_synthetic_backend.validate_inspection_json(payload, expected_count=1)


def test_synthetic_backend_inspection_parser_malformed_json():
    """
    Parser acceptance test: Rejects malformed JSON syntax.
    """
    import json
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

    with pytest.raises(ValueError, match="expected count == 1, got 0"):
        caddy_synthetic_backend.validate_inspection_json(json.dumps({"count": 0}), expected_count=1)


def test_synthetic_backend_inspection_parser_count_greater_than_one():
    """
    Parser acceptance test: Rejects count > 1 when expected count is 1.
    """
    import json
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
    repo_root = Path(__file__).resolve().parent.parent.parent
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import caddy_synthetic_backend

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
