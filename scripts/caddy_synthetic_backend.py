#!/usr/bin/env python3
"""
scripts/caddy_synthetic_backend.py

Minimal, zero-dependency synthetic HTTP backend for isolated Caddy verification.
Listens on both port 8000 (upstream for backend:8000) and port 3000 (upstream for frontend:3000).
Records incoming requests, exact body sizes, and headers for verification by CI test runners.
"""
import sys
import json
import os
import threading
from typing import Optional, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

# Shared thread-safe request log
_LOG_LOCK = threading.Lock()
REQUEST_LOG = []


class SyntheticBackendHandler(BaseHTTPRequestHandler):
    server_version = "LivoSyntheticBackend/1.0"

    def log_message(self, format, *args):
        # Override to keep test output clean; write directly to stderr with prefix
        sys.stderr.write(f"[synthetic_backend:{self.server.server_port}] {format % args}\n")

    def _send_json(self, status_code: int, data: dict):
        response_body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def do_GET(self):
        # Inspection endpoint to retrieve recorded requests
        if self.path == "/inspect/requests":
            with _LOG_LOCK:
                self._send_json(200, {
                    "count": len(REQUEST_LOG),
                    "requests": list(REQUEST_LOG)
                })
            return

        # Health endpoint
        if self.path.startswith("/health"):
            self._send_json(200, {
                "status": "healthy",
                "service": "synthetic_backend",
                "port": self.server.server_port
            })
            return

        # Default GET handler for proxied routes (/api/*, /docs*, etc.)
        record = {
            "method": "GET",
            "path": self.path,
            "port": self.server.server_port,
            "content_length": self.headers.get("Content-Length"),
            "body_bytes_read": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        with _LOG_LOCK:
            REQUEST_LOG.append(record)

        self._send_json(200, {
            "status": "ok",
            "message": "GET received by synthetic backend",
            "path": self.path,
            "port": self.server.server_port
        })

    def do_POST(self):
        # Endpoint to clear recorded request log
        if self.path == "/inspect/clear":
            with _LOG_LOCK:
                REQUEST_LOG.clear()
            self._send_json(200, {"status": "cleared", "count": 0})
            return

        # Read body if present
        content_length_header = self.headers.get("Content-Length")
        body_bytes_read = 0
        if content_length_header:
            try:
                length = int(content_length_header)
                remaining = length
                chunk_size = 64 * 1024
                while remaining > 0:
                    read_len = min(remaining, chunk_size)
                    chunk = self.rfile.read(read_len)
                    if not chunk:
                        break
                    body_bytes_read += len(chunk)
                    remaining -= len(chunk)
            except ValueError:
                pass

        record = {
            "method": "POST",
            "path": self.path,
            "port": self.server.server_port,
            "content_length": content_length_header,
            "body_bytes_read": body_bytes_read,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        with _LOG_LOCK:
            REQUEST_LOG.append(record)

        self._send_json(200, {
            "status": "received",
            "path": self.path,
            "port": self.server.server_port,
            "bytes_received": body_bytes_read
        })


def _reject_duplicate_keys(pairs):
    seen = set()
    result = {}
    for key, val in pairs:
        if key in seen:
            raise ValueError(f"Duplicate key {key!r} detected in JSON object")
        seen.add(key)
        result[key] = val
    return result


def _find_body_bytes_read(data: dict):
    """
    Locates body_bytes_read in top-level dict or in the first element of requests array.
    Returns tuple: (present: bool, value: Any).
    """
    if "body_bytes_read" in data:
        return True, data["body_bytes_read"]
    if "requests" in data and isinstance(data["requests"], list) and len(data["requests"]) > 0:
        first_req = data["requests"][0]
        if isinstance(first_req, dict) and "body_bytes_read" in first_req:
            return True, first_req["body_bytes_read"]
    return False, None


def validate_inspection_json(
    raw_text: str,
    expected_count: int = 1,
    expected_bytes: Optional[int] = None,
    require_bytes: bool = False,
) -> dict:
    """
    Validates synthetic backend /inspect/requests JSON response:
    - Must be a non-empty string.
    - Must be valid JSON object (dict).
    - Rejects duplicate JSON keys at any level (including nested objects).
    - Must contain 'count' field.
    - 'count' must be an integer (and not a boolean).
    - 'count' must be non-negative (>= 0).
    - 'count' must equal expected_count exactly.
    - If expected_bytes is provided (or require_bytes=True), 'body_bytes_read'
      must be present in the response (top-level or inside requests[0]).
    - If 'body_bytes_read' is present (or required), it must be an integer (and not a boolean),
      non-negative (>= 0), and equal to expected_bytes when expected_bytes is specified.
    Returns parsed dictionary or raises ValueError / json.JSONDecodeError.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Empty or whitespace-only response received from backend inspection")

    data = json.loads(raw_text, object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object (dict), got {type(data).__name__}")

    if "count" not in data:
        raise ValueError("Missing required field 'count' in inspection response")

    count = data["count"]
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError(f"Field 'count' must be an integer, got {type(count).__name__} ({count!r})")

    if count < 0:
        raise ValueError(f"Field 'count' must be a non-negative integer, got {count}")

    if count != expected_count:
        raise ValueError(f"Inspection assertion failed: expected count == {expected_count}, got {count}")

    # Validate body_bytes_read across requests array if present
    if "requests" in data and isinstance(data["requests"], list):
        for idx, req in enumerate(data["requests"]):
            if isinstance(req, dict) and "body_bytes_read" in req:
                b_val = req["body_bytes_read"]
                if isinstance(b_val, bool) or not isinstance(b_val, int):
                    raise ValueError(f"Field 'body_bytes_read' in requests[{idx}] must be an integer, got {type(b_val).__name__} ({b_val!r})")
                if b_val < 0:
                    raise ValueError(f"Field 'body_bytes_read' in requests[{idx}] must be a non-negative integer, got {b_val}")

    # Top-level or target body_bytes_read validation
    bytes_found, bytes_val = _find_body_bytes_read(data)

    if expected_bytes is not None or require_bytes:
        if not bytes_found:
            raise ValueError("Missing required field 'body_bytes_read' in inspection response")

    if bytes_found:
        if isinstance(bytes_val, bool) or not isinstance(bytes_val, int):
            raise ValueError(f"Field 'body_bytes_read' must be an integer, got {type(bytes_val).__name__} ({bytes_val!r})")
        if bytes_val < 0:
            raise ValueError(f"Field 'body_bytes_read' must be a non-negative integer, got {bytes_val}")
        if expected_bytes is not None and bytes_val != expected_bytes:
            raise ValueError(f"Byte count assertion failed: expected body_bytes_read == {expected_bytes}, got {bytes_val}")

    return data


def run_dual(port_backend: int = 8000, port_frontend: int = 3000):
    server_backend = HTTPServer(("0.0.0.0", port_backend), SyntheticBackendHandler)
    server_frontend = HTTPServer(("0.0.0.0", port_frontend), SyntheticBackendHandler)

    t1 = threading.Thread(target=server_backend.serve_forever, daemon=True)
    t2 = threading.Thread(target=server_frontend.serve_forever, daemon=True)
    t1.start()
    t2.start()

    print(f"[synthetic_backend] Dual listeners active on 0.0.0.0:{port_backend} (backend) and 0.0.0.0:{port_frontend} (frontend)...", flush=True)

    try:
        t1.join()
    except KeyboardInterrupt:
        print("\n[synthetic_backend] Shutting down.", flush=True)
    finally:
        server_backend.server_close()
        server_frontend.server_close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--validate-inspect", "--validate-json"):
        args = sys.argv[2:]
        expected_count = 1
        expected_bytes = None
        raw_input = None

        idx = 0
        while idx < len(args):
            arg = args[idx]
            if arg in ("--expected-bytes", "--bytes"):
                idx += 1
                if idx < len(args):
                    expected_bytes = int(args[idx])
            elif arg.startswith("--expected-bytes="):
                expected_bytes = int(arg.split("=", 1)[1])
            elif expected_count == 1 and arg.isdigit() and idx == 0:
                expected_count = int(arg)
            elif expected_bytes is None and arg.isdigit() and idx == 1:
                expected_bytes = int(arg)
            else:
                raw_input = arg
            idx += 1

        if raw_input is None:
            raw_input = sys.stdin.read()

        try:
            validated = validate_inspection_json(
                raw_input,
                expected_count=expected_count,
                expected_bytes=expected_bytes,
            )
            req_count = len(validated.get("requests", []))
            bytes_msg = f", verified body_bytes_read == {expected_bytes}" if expected_bytes is not None else ""
            print(f"[synthetic_backend_validator] Valid JSON; verified count == {expected_count}{bytes_msg} (requests list: {req_count} entries)")
            sys.exit(0)
        except Exception as err:
            sys.stderr.write(f"::error::Inspection validation failed: {err}\n")
            sys.exit(1)

    port_backend = int(os.environ.get("PORT_BACKEND", os.environ.get("PORT", "8000")))
    port_frontend = int(os.environ.get("PORT_FRONTEND", "3000"))
    run_dual(port_backend, port_frontend)
