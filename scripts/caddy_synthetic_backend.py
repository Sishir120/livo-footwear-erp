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

# Shared thread-safe request log and sequence counter
_LOG_LOCK = threading.Lock()
REQUEST_LOG = []
_REQUEST_COUNTER = 0


class SyntheticBackendHandler(BaseHTTPRequestHandler):
    server_version = "LivoSyntheticBackend/1.0"
    timeout = 10

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
        global _REQUEST_COUNTER
        # Inspection endpoint to retrieve recorded requests
        if self.path == "/inspect/requests":
            with _LOG_LOCK:
                self._send_json(200, {
                    "count": len(REQUEST_LOG),
                    "completed_count": sum(1 for r in REQUEST_LOG if r.get("completed")),
                    "partial_count": sum(1 for r in REQUEST_LOG if not r.get("completed")),
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
            "request_id": None,
            "method": "GET",
            "path": self.path,
            "port": self.server.server_port,
            "content_length": self.headers.get("Content-Length"),
            "bytes_expected": 0,
            "body_bytes_read": 0,
            "completed": True,
            "truncated": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        with _LOG_LOCK:
            _REQUEST_COUNTER += 1
            record["request_id"] = _REQUEST_COUNTER
            REQUEST_LOG.append(record)

        self._send_json(200, {
            "status": "ok",
            "message": "GET received by synthetic backend",
            "path": self.path,
            "port": self.server.server_port
        })

    def do_POST(self):
        global _REQUEST_COUNTER
        # Endpoint to clear recorded request log
        if self.path == "/inspect/clear":
            with _LOG_LOCK:
                _REQUEST_COUNTER = 0
                REQUEST_LOG.clear()
            self._send_json(200, {"status": "cleared", "count": 0})
            return

        # Read body if present
        content_length_header = self.headers.get("Content-Length")
        transfer_encoding = self.headers.get("Transfer-Encoding", "").lower()
        body_bytes_read = 0
        bytes_expected = None
        completed = True
        truncated = False

        if "chunked" in transfer_encoding:
            # Handle chunked transfer-encoding stream per strict HTTP/1.1 (RFC 9112 §7.1)
            try:
                while True:
                    line = self.rfile.readline()
                    if not line:
                        truncated = True
                        completed = False
                        break
                    if not line.endswith(b"\r\n"):
                        # Strict HTTP/1.1 requires chunk-size line to end in CRLF
                        truncated = True
                        completed = False
                        break
                    line_clean = line.split(b";")[0].strip()
                    if not line_clean:
                        truncated = True
                        completed = False
                        break
                    try:
                        chunk_len = int(line_clean, 16)
                    except ValueError:
                        completed = False
                        truncated = True
                        break

                    if chunk_len < 0:
                        completed = False
                        truncated = True
                        break

                    if chunk_len == 0:
                        # Terminal chunk: consume trailing trailers / CRLF
                        saw_terminal_crlf = False
                        while True:
                            trailer = self.rfile.readline()
                            if not trailer:
                                # Premature EOF during trailer / terminal framing
                                break
                            if trailer == b"\r\n":
                                # Strict HTTP/1.1 terminal CRLF separator
                                saw_terminal_crlf = True
                                break
                            if not trailer.endswith(b"\r\n"):
                                # Trailer line without strict CRLF or bare LF terminal separator
                                break
                            # Valid trailer field ending in CRLF: continue consuming until terminal CRLF
                        if not saw_terminal_crlf:
                            completed = False
                            truncated = True
                        break

                    chunk_data = self.rfile.read(chunk_len)
                    body_bytes_read += len(chunk_data)
                    if len(chunk_data) < chunk_len:
                        truncated = True
                        completed = False
                        break

                    # Consume and validate strict CRLF terminator following chunk data
                    crlf = self.rfile.readline()
                    if crlf != b"\r\n":
                        truncated = True
                        completed = False
                        break
            except Exception:
                completed = False
                truncated = True
        elif content_length_header is not None:
            try:
                # Handle comma-separated duplicate headers (e.g. "100, 100")
                if "," in content_length_header:
                    parts = [p.strip() for p in content_length_header.split(",")]
                    if len(set(parts)) == 1 and parts[0].isdigit():
                        length = int(parts[0])
                    else:
                        raise ValueError(f"Conflicting or malformed duplicate Content-Length: {content_length_header}")
                else:
                    length = int(content_length_header)

                if length < 0:
                    raise ValueError(f"Negative Content-Length not permitted: {length}")

                bytes_expected = length
                remaining = length
                chunk_size = 64 * 1024
                while remaining > 0:
                    read_len = min(remaining, chunk_size)
                    chunk = self.rfile.read(read_len)
                    if not chunk:
                        # Premature EOF: connection closed by upstream/proxy mid-stream
                        break
                    body_bytes_read += len(chunk)
                    remaining -= len(chunk)
                if remaining > 0:
                    completed = False
                    truncated = True
            except ValueError:
                completed = False
                truncated = False

        record = {
            "request_id": None,
            "method": "POST",
            "path": self.path,
            "port": self.server.server_port,
            "content_length": content_length_header,
            "transfer_encoding": transfer_encoding or None,
            "bytes_expected": bytes_expected,
            "body_bytes_read": body_bytes_read,
            "completed": completed,
            "truncated": truncated,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        with _LOG_LOCK:
            _REQUEST_COUNTER += 1
            record["request_id"] = _REQUEST_COUNTER
            REQUEST_LOG.append(record)

        try:
            self._send_json(200, {
                "status": "received" if completed else "partial",
                "path": self.path,
                "port": self.server.server_port,
                "bytes_received": body_bytes_read,
                "completed": completed,
                "truncated": truncated
            })
        except (BrokenPipeError, ConnectionResetError):
            pass


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
        req_summaries = []
        for i, r in enumerate(data.get("requests", [])):
            if isinstance(r, dict):
                m = r.get("method", "?")
                p = r.get("path", "?")
                b = r.get("body_bytes_read", "?")
                exp = r.get("bytes_expected", r.get("content_length", "?"))
                comp = r.get("completed", "?")
                trunc = r.get("truncated", "?")
                req_summaries.append(
                    f"#{i+1} {m} {p} (read {b}/{exp} bytes, completed={comp}, truncated={trunc})"
                )
        details_str = f". Recorded requests: [{'; '.join(req_summaries)}]" if req_summaries else ""
        raise ValueError(
            f"Inspection assertion failed: expected count == {expected_count}, got {count}{details_str}"
        )

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


def validate_case_c_inspection_json(
    raw_text: str,
    case_c_path: str = "/api/test_streaming_oversized",
    max_bytes: int = 10000000,
    expected_case_a_bytes: int = 1048576,
    required_outcome: Optional[str] = None,
    client_status: Optional[str] = None,
    curl_exit: Optional[int] = None,
    expected_prior_requests: int = 1,
) -> dict:
    """
    Validates synthetic backend inspection response following streaming / chunked test Case C.
    Enforces unambiguous outcome classification across three distinct cases:

    Outcome C1 (Early rejection before upstream initiation):
    - Client status: HTTP 413 (or clean rejection before forwarding).
    - Exactly expected_prior_requests recorded in backend (Case C was rejected before upstream).
    - Case A record remains unchanged (POST, exact bytes, completed=True, truncated=False).
    - Reported explicitly as "Outcome C1: Early rejection before upstream initiation".

    Outcome C2 (Streaming termination with HTTP 413):
    - Client status: HTTP 413.
    - Exactly expected_prior_requests + 1 requests recorded in backend.
    - Case A record (index 0) remains unchanged.
    - Case C record (index expected_prior_requests) must have:
      - path matching case_c_path exactly
      - body_bytes_read <= max_bytes
      - completed is False
      - truncated is True
    - Reported explicitly as "Outcome C2: Streaming termination (HTTP 413; upstream stream truncated <= 10MB / 10,000,000 bytes)".

    Outcome C3 (Connection failure / reset mid-upload):
    - Client status: '000' (or non-zero curl exit code / connection reset).
    - Exactly expected_prior_requests + 1 requests recorded in backend.
    - Case A record remains unchanged.
    - Case C record has body_bytes_read <= max_bytes, completed=False, truncated=True.
    - Reported explicitly as "Outcome C3: Connection failure / stream severed mid-upload".

    Fails closed if:
    - JSON is empty, malformed, non-dict, or contains duplicate keys.
    - count < expected_prior_requests (prior requests missing).
    - count > expected_prior_requests + 1 (spurious unexpected requests).
    - Case A payload or completion status was altered.
    - Client status is unexpected (e.g. 200, 500, 502).
    - required_outcome is set and doesn't match the observed outcome.
    - Case C record fails any streaming attribute (excess bytes, completed=True, truncated=False, path mismatch).
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Empty or whitespace-only response received from backend inspection")

    data = json.loads(raw_text, object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object (dict), got {type(data).__name__}")

    if "count" not in data:
        raise ValueError("Missing required field 'count' in inspection response")

    count = data["count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError(f"Field 'count' must be a non-negative integer, got {count!r}")

    requests = data.get("requests", [])
    if not isinstance(requests, list):
        raise ValueError("Field 'requests' must be a list")

    if count < expected_prior_requests or len(requests) < expected_prior_requests:
        raise ValueError(f"Invalid inspection state: expected at least {expected_prior_requests} prior request(s), got count={count}, len(requests)={len(requests)})")

    # Invariant: Case A (request index 0) must remain completely intact and unchanged
    req_a = requests[0]
    if not isinstance(req_a, dict):
        raise ValueError("Case A request record must be an object")
    if req_a.get("method") != "POST":
        raise ValueError(f"Case A method modified: expected 'POST', got {req_a.get('method')!r}")
    if req_a.get("body_bytes_read") != expected_case_a_bytes:
        raise ValueError(
            f"Case A payload modified: expected {expected_case_a_bytes} bytes, got {req_a.get('body_bytes_read')}"
        )
    if req_a.get("completed") is not True:
        raise ValueError(f"Case A completed status modified: expected True, got {req_a.get('completed')}")
    if req_a.get("truncated") is not False:
        raise ValueError(f"Case A truncated status modified: expected False, got {req_a.get('truncated')}")

    if count > expected_prior_requests + 1 or len(requests) > expected_prior_requests + 1:
        req_summaries = []
        for i, r in enumerate(requests):
            if isinstance(r, dict):
                req_summaries.append(
                    f"#{i+1} {r.get('method')} {r.get('path')} (read {r.get('body_bytes_read')} bytes, completed={r.get('completed')})"
                )
        raise ValueError(
            f"Unexpected request count after Case C: expected {expected_prior_requests} or {expected_prior_requests + 1}, got count={count}, len(requests)={len(requests)}. Requests: [{'; '.join(req_summaries)}]"
        )

    # Validate client status if provided
    if client_status is not None:
        client_status_str = str(client_status).strip()
        if client_status_str not in ("413", "000", ""):
            raise ValueError(f"Unexpected client status for Case C: expected '413' or '000', got '{client_status_str}'")

    # Classify outcome
    if count == expected_prior_requests and len(requests) == expected_prior_requests:
        observed_outcome = "C1"
        outcome_desc = f"Outcome C1: Early rejection before upstream initiation (0 Case C requests reached backend; backend count remained {expected_prior_requests})"
        if required_outcome:
            req_norm = required_outcome.strip().lower()
            if req_norm not in ("c1", "outcome_1", "early_rejection", "any"):
                raise ValueError(
                    f"Outcome mismatch: required '{required_outcome}', but observed Outcome C1 (request rejected before upstream initiation; backend count remained {expected_prior_requests})"
                )
        return {
            "outcome": observed_outcome,
            "description": outcome_desc,
            "count": expected_prior_requests,
            "client_status": client_status,
            "curl_exit": curl_exit,
            "case_a_record": req_a,
            "case_c_record": None,
            "bytes_received": 0,
            "data": data,
        }

    # Otherwise count == expected_prior_requests + 1 -> Streaming truncation observed at backend
    req_c = requests[expected_prior_requests]
    if not isinstance(req_c, dict):
        raise ValueError("Case C request record must be an object")

    actual_path = req_c.get("path")
    if actual_path != case_c_path:
        raise ValueError(f"Case C path mismatch: expected {case_c_path!r}, got {actual_path!r}")

    bytes_read = req_c.get("body_bytes_read", 0)
    if isinstance(bytes_read, bool) or not isinstance(bytes_read, int) or bytes_read < 0:
        raise ValueError(f"Invalid body_bytes_read in Case C: {bytes_read!r}")

    if bytes_read > max_bytes:
        raise ValueError(f"Backend received excess bytes in Case C: {bytes_read} > {max_bytes}")

    if req_c.get("completed") is not False:
        raise ValueError("Chunked request exceeding streaming limit must have completed=False")

    if req_c.get("truncated") is not True:
        raise ValueError("Chunked request exceeding streaming limit must have truncated=True")

    # Determine whether client received HTTP 413 (C2) or connection reset / 000 (C3)
    if client_status is not None and str(client_status).strip() in ("000", ""):
        observed_outcome = "C3"
        outcome_desc = f"Outcome C3: Connection failure / stream severed mid-upload (client status 000, curl exit {curl_exit}; upstream stream truncated at {bytes_read} bytes <= {max_bytes})"
    elif client_status is not None and str(client_status).strip() == "413":
        observed_outcome = "C2"
        outcome_desc = f"Outcome C2: Streaming termination (HTTP 413 received by client; upstream stream truncated at {bytes_read} bytes <= {max_bytes})"
    else:
        # Default without explicit client_status: C2 (streaming termination verified at backend)
        observed_outcome = "C2"
        outcome_desc = f"Outcome C2: Streaming termination (upstream stream initiated and truncated at {bytes_read} bytes <= {max_bytes})"

    if required_outcome:
        req_norm = required_outcome.strip().lower()
        valid_match = False
        if req_norm == "any":
            valid_match = True
        elif req_norm in ("c2", "outcome_2", "stream_truncated") and observed_outcome in ("C2", "C3"):
            valid_match = True
        elif req_norm in ("c3", "connection_failure", "connection_reset") and observed_outcome == "C3":
            valid_match = True
        elif req_norm == observed_outcome.lower():
            valid_match = True

        if not valid_match:
            raise ValueError(
                f"Outcome mismatch: required '{required_outcome}', but observed Outcome {observed_outcome} ({outcome_desc})"
            )

    return {
        "outcome": observed_outcome,
        "description": outcome_desc,
        "count": expected_prior_requests + 1,
        "client_status": client_status,
        "curl_exit": curl_exit,
        "case_a_record": req_a,
        "case_c_record": req_c,
        "bytes_received": bytes_read,
        "data": data,
    }


def validate_streaming_inspection_json(
    raw_text: str,
    max_bytes: int = 10000000,
) -> dict:
    """Backward-compatible wrapper delegating to validate_case_c_inspection_json."""
    return validate_case_c_inspection_json(raw_text, max_bytes=max_bytes)["data"]


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
    if len(sys.argv) > 1 and sys.argv[1] in ("--validate-case-c", "--validate-streaming"):
        args = sys.argv[2:]
        max_bytes = 10000000
        case_c_path = "/api/test_streaming_oversized"
        required_outcome = None
        expected_case_a_bytes = 1048576
        expected_prior_requests = 1
        client_status = None
        curl_exit = None

        idx = 0
        while idx < len(args):
            arg = args[idx]
            if arg in ("--max-bytes", "--bytes"):
                idx += 1
                if idx < len(args):
                    max_bytes = int(args[idx])
            elif arg.startswith("--max-bytes="):
                max_bytes = int(arg.split("=", 1)[1])
            elif arg in ("--case-c-path", "--path"):
                idx += 1
                if idx < len(args):
                    case_c_path = args[idx]
            elif arg.startswith("--case-c-path="):
                case_c_path = arg.split("=", 1)[1]
            elif arg in ("--client-status", "--status"):
                idx += 1
                if idx < len(args):
                    client_status = args[idx]
            elif arg.startswith("--client-status="):
                client_status = arg.split("=", 1)[1]
            elif arg in ("--curl-exit", "--exit-code"):
                idx += 1
                if idx < len(args):
                    curl_exit = int(args[idx])
            elif arg.startswith("--curl-exit="):
                curl_exit = int(arg.split("=", 1)[1])
            elif arg in ("--require-outcome", "--outcome"):
                idx += 1
                if idx < len(args):
                    required_outcome = args[idx]
            elif arg.startswith("--require-outcome="):
                required_outcome = arg.split("=", 1)[1]
            elif arg in ("--expected-prior-requests", "--prior-count"):
                idx += 1
                if idx < len(args):
                    expected_prior_requests = int(args[idx])
            elif arg.startswith("--expected-prior-requests="):
                expected_prior_requests = int(arg.split("=", 1)[1])
            elif arg.startswith("--prior-count="):
                expected_prior_requests = int(arg.split("=", 1)[1])
            elif arg.isdigit() and idx == 0:
                max_bytes = int(arg)
            idx += 1

        raw_input = sys.stdin.read()
        try:
            result = validate_case_c_inspection_json(
                raw_input,
                case_c_path=case_c_path,
                max_bytes=max_bytes,
                expected_case_a_bytes=expected_case_a_bytes,
                required_outcome=required_outcome,
                client_status=client_status,
                curl_exit=curl_exit,
                expected_prior_requests=expected_prior_requests,
            )
            outcome = result["outcome"]
            desc = result["description"]
            print(f"[synthetic_backend_validator] CLASSIFIED OUTCOME: {outcome} ({desc})")
            if outcome in ("C2", "C3", "outcome_2"):
                c_rec = result["case_c_record"]
                print(f"[synthetic_backend_validator] {outcome} Evidence: Case C endpoint '{c_rec.get('path')}' received {c_rec.get('body_bytes_read')}/{max_bytes} bytes (completed={c_rec.get('completed')}, truncated={c_rec.get('truncated')}, client_status='{result.get('client_status')}', curl_exit={result.get('curl_exit')})")
            elif outcome in ("C1", "outcome_1"):
                print(f"[synthetic_backend_validator] {outcome} Evidence: 0 requests reached upstream backend (total backend count remained 1, Case A preserved, client_status='{result.get('client_status')}', curl_exit={result.get('curl_exit')})")
            sys.exit(0)
        except Exception as err:
            sys.stderr.write(f"::error::Case C validation failed: {err}\n")
            sys.exit(1)

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
