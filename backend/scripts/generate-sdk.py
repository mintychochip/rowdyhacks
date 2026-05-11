#!/usr/bin/env python3
"""Generate a TypeScript SDK from the running FastAPI OpenAPI spec.

Usage:
    python backend/scripts/generate-sdk.py

The script introspects app.main:app in-process, extracts app.openapi(),
and writes sdk/openhack-client.ts.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any


def _resolve_ref(spec: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve a $ref to the actual schema object."""
    if "$ref" not in schema:
        return schema
    ref = schema["$ref"]
    if not ref.startswith("#/components/schemas/"):
        return schema
    name = ref.split("/")[-1]
    return spec.get("components", {}).get("schemas", {}).get(name, schema)


def _openapi_type_to_ts(spec: dict[str, Any], schema: dict[str, Any]) -> str:
    """Convert an OpenAPI JSON Schema fragment to a TypeScript type string."""
    if schema is None:
        return "unknown"

    schema = _resolve_ref(spec, schema)

    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/components/schemas/"):
            return ref.split("/")[-1]
        return "unknown"

    # Handle anyOf / oneOf with null -> optional union
    any_of = schema.get("anyOf") or schema.get("oneOf")
    if any_of:
        parts: list[str] = []
        has_null = False
        for sub in any_of:
            if sub.get("type") == "null":
                has_null = True
                continue
            parts.append(_openapi_type_to_ts(spec, sub))
        ts = " | ".join(dict.fromkeys(parts)) if parts else "unknown"
        if has_null:
            ts += " | null"
        return ts

    schema_type = schema.get("type")
    if schema_type == "string":
        fmt = schema.get("format")
        if fmt == "binary":
            return "File | Blob"
        return "string"
    if schema_type == "integer":
        return "number"
    if schema_type == "number":
        return "number"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "array":
        items = schema.get("items", {})
        return f"{_openapi_type_to_ts(spec, items)}[]"
    if schema_type == "object":
        additional = schema.get("additionalProperties")
        if additional:
            val_type = _openapi_type_to_ts(spec, additional)
            return f"Record<string, {val_type}>"
        props = schema.get("properties")
        if not props:
            return "Record<string, unknown>"
        # Inline object shape (used for nested objects)
        fields = []
        for k, v in props.items():
            optional = k not in schema.get("required", [])
            ts_type = _openapi_type_to_ts(spec, v)
            fields.append(f"{k}{'?' if optional else ''}: {ts_type}")
        return "{ " + "; ".join(fields) + " }"

    return "unknown"


def _generate_interface(name: str, schema: dict[str, Any]) -> str:
    """Generate a TypeScript interface from an OpenAPI schema object."""
    lines: list[str] = []
    description = schema.get("description", "")
    if description:
        for doc_line in description.strip().splitlines():
            lines.append(f"/** {doc_line.rstrip()} */")
    lines.append(f"export interface {name} {{")
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    for prop_name, prop_schema in props.items():
        optional = prop_name not in required
        ts_type = _openapi_type_to_ts({}, prop_schema)  # interfaces don't need spec ref resolution
        comment = prop_schema.get("description", "")
        if comment:
            lines.append(f"  /** {comment.strip()} */")
        lines.append(f"  {prop_name}{'?' if optional else ''}: {ts_type};")
    lines.append("}")
    return "\n".join(lines)


def _to_camel_case(snake: str) -> str:
    """Convert snake_case to camelCase."""
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _generate_method(spec: dict[str, Any], path: str, method: str, op: dict[str, Any]) -> str:
    """Generate a TypeScript client method from an OpenAPI operation."""
    operation_id = op.get("operationId", "")
    summary = op.get("summary", "")
    description = op.get("description", "")
    tags = op.get("tags", [])

    # Derive a clean method name
    method_name = _to_camel_case(operation_id)
    # Strip trailing path suffix noise if present
    method_name = re.sub(r"_api_.*$", "", method_name)
    if not method_name:
        method_name = method.lower() + _to_camel_case(path.replace("/", "_").strip("_"))

    # Collect parameters
    path_params: list[dict[str, Any]] = []
    query_params: list[dict[str, Any]] = []
    header_params: list[dict[str, Any]] = []
    for param in op.get("parameters", []):
        if param.get("in") == "path":
            path_params.append(param)
        elif param.get("in") == "query":
            query_params.append(param)
        elif param.get("in") == "header":
            header_params.append(param)

    # Request body
    request_body = op.get("requestBody", {})
    body_schema: dict[str, Any] | None = None
    body_content_type = "application/json"
    if request_body:
        content = request_body.get("content", {})
        for ct, info in content.items():
            body_schema = _resolve_ref(spec, info.get("schema", {}))
            body_content_type = ct
            break

    # Response type
    responses = op.get("responses", {})
    response_schema: dict[str, Any] | None = None
    for code in ["200", "201", "204"]:
        if code in responses:
            content = responses[code].get("content", {})
            for ct, info in content.items():
                response_schema = info.get("schema")
                break
            break

    return_type = _openapi_type_to_ts(spec, response_schema) if response_schema else "unknown"
    # Special overrides for endpoints that return plain text or empty schema
    if path == "/api/config/theme.css" and method == "get":
        return_type = "string"
    if path == "/api/config/custom.css" and method == "get":
        return_type = "string"
    if path == "/api/config/manifest.json" and method == "get":
        return_type = "Record<string, unknown>"

    # Build signature
    args: list[str] = []
    # Path args
    for p in path_params:
        ts_type = _openapi_type_to_ts(spec, p.get("schema", {}))
        args.append(f"{p['name']}: {ts_type}")
    # Query args
    for p in query_params:
        ts_type = _openapi_type_to_ts(spec, p.get("schema", {}))
        optional = p.get("required") is not True
        args.append(f"{p['name']}{'?' if optional else ''}: {ts_type}")
    # Body arg
    if body_schema:
        if body_content_type == "multipart/form-data":
            # Handle form data with File fields specially
            props = body_schema.get("properties", {})
            req = set(body_schema.get("required", []))
            for fname, fschema in props.items():
                ts_type = _openapi_type_to_ts(spec, fschema)
                optional = fname not in req
                args.append(f"{fname}{'?' if optional else ''}: {ts_type}")
        else:
            ts_type = _openapi_type_to_ts(spec, body_schema)
            args.append(f"body: {ts_type}")

    doc_lines: list[str] = []
    if summary:
        doc_lines.append(f"{method.upper()} {path} — {summary}")
    else:
        doc_lines.append(f"{method.upper()} {path}")
    if description:
        for dline in description.strip().splitlines():
            doc_lines.append(dline.rstrip())
    if tags:
        doc_lines.append(f"Tags: {', '.join(tags)}")

    sig = f"async {method_name}({', '.join(args)}): Promise<{return_type}>"

    lines: list[str] = []
    lines.append("  /**")
    for dl in doc_lines:
        lines.append(f"   * {dl}")
    lines.append("   */")
    lines.append(f"  {sig} {{")

    # Headers
    headers_lines: list[str] = []
    if body_content_type == "application/json":
        headers_lines.append("        'Content-Type': 'application/json',")
    if method == "get" or return_type != "string":
        headers_lines.append("        'Accept': 'application/json',")

    # Request init
    init_parts: list[str] = []
    init_parts.append(f"      method: '{method.upper()}',")
    if headers_lines:
        init_parts.append("      headers: {")
        init_parts.extend(headers_lines)
        init_parts.append("      },")

    # URL construction
    if path_params:
        url_path = path
        for p in path_params:
            pname = p["name"]
            url_path = url_path.replace("{" + pname + "}", f"${{{pname}}}")
        url_expr = f"`${{this.baseUrl}}{url_path}`"
    else:
        url_expr = f"`${{this.baseUrl}}{path}`"

    # Query params
    if query_params:
        lines.append("    const params = new URLSearchParams();")
        for p in query_params:
            pname = p["name"]
            lines.append(f"    if ({pname} != null) params.append('{pname}', String({pname}));")
        url_expr = f"`${{this.baseUrl}}{path}` + (params.toString() ? `?${{params.toString()}}` : '')"

    # Body
    if body_content_type == "multipart/form-data":
        lines.append("    const formData = new FormData();")
        for fname in body_schema.get("properties", {}):
            lines.append(f"    if ({fname} != null) formData.append('{fname}', {fname});")
        init_parts.append("      body: formData,")
    elif body_schema:
        init_parts.append("      body: JSON.stringify(body),")

    lines.append(f"    const url = {url_expr};")
    lines.append("    const res = await fetch(url, {")
    lines.extend(init_parts)
    lines.append("    });")
    lines.append("    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);")

    if return_type == "string":
        lines.append("    return res.text();")
    elif return_type == "void" or (return_type == "unknown" and "204" in responses):
        lines.append("    return;")
    else:
        lines.append("    return res.json();")

    lines.append("  }")
    return "\n".join(lines)


def _required_convenience_methods() -> str:
    """Return the required convenience methods with exact signatures."""
    return """
  /** GET /api/config */
  async getConfig(): Promise<Record<string, string>> {
    return this.getAllConfigApiConfigGet();
  }

  /** GET /api/config/theme.css */
  async getThemeCss(): Promise<string> {
    return this.getThemeCssApiConfigThemeCssGet();
  }

  /** PUT /api/config */
  async updateConfig(updates: Record<string, string>): Promise<{ updated: string[] }> {
    return this.updateConfigApiConfigPut(updates);
  }

  /** POST /api/config/assets */
  async uploadAsset(file: File | Blob, key?: string | null): Promise<{ key: string; url: string }> {
    return this.uploadAssetApiConfigAssetsPost(file, key);
  }

  /** GET /api/config/branding */
  async getBranding(): Promise<BrandingResponse> {
    return this.getBrandingApiConfigBrandingGet();
  }
"""


def generate_sdk(spec: dict[str, Any]) -> str:
    """Generate the full TypeScript SDK source."""
    parts: list[str] = []
    parts.append("// Auto-generated TypeScript SDK for OpenHack API")
    parts.append("// Generated from FastAPI OpenAPI spec — do not edit manually.")
    parts.append("")
    parts.append("/* eslint-disable */")
    parts.append("")

    # Interfaces for all schemas
    schemas = spec.get("components", {}).get("schemas", {})
    for name in sorted(schemas.keys()):
        schema = schemas[name]
        # Skip internal form-data body schemas unless useful
        if name.startswith("Body_"):
            continue
        parts.append(_generate_interface(name, schema))
        parts.append("")

    # Client class
    parts.append("export class OpenHackClient {")
    parts.append("  private baseUrl: string;")
    parts.append("")
    parts.append("  /**")
    parts.append("   * Create a new OpenHack API client.")
    parts.append("   * @param baseUrl — API base URL (default: https://localhost/api)")
    parts.append("   */")
    parts.append("  constructor(baseUrl: string = 'https://localhost/api') {")
    parts.append("    this.baseUrl = baseUrl.replace(/\\/$/, '');")
    parts.append("  }")
    parts.append("")

    # Generate methods for every path/operation
    paths = spec.get("paths", {})
    for path in sorted(paths.keys()):
        methods = paths[path]
        for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
            if method in methods:
                parts.append(_generate_method(spec, path, method, methods[method]))
                parts.append("")

    # Add required convenience methods
    parts.append(_required_convenience_methods())

    parts.append("}")
    parts.append("")
    parts.append("export default OpenHackClient;")
    return "\n".join(parts)


def main() -> int:
    backend_dir = Path(__file__).resolve().parent.parent
    project_root = backend_dir.parent
    sdk_dir = project_root / "sdk"
    sdk_dir.mkdir(parents=True, exist_ok=True)
    out_file = sdk_dir / "openhack-client.ts"

    sys.path.insert(0, str(backend_dir))
    from app.main import app

    spec = app.openapi()
    ts_source = generate_sdk(spec)
    out_file.write_text(ts_source, encoding="utf-8")

    print(f"Generated SDK: {out_file}")
    print(f"  Routes: {len(spec.get('paths', {}))}")
    print(f"  Schemas: {len(spec.get('components', {}).get('schemas', {}))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
