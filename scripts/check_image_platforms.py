import json
import os
import re
import ssl
import urllib.parse
import urllib.request

import yaml

import platform


def normalize_arch(machine: str | None = None) -> str:
    m = (machine or platform.machine() or "").lower()
    if m in {"x86_64", "amd64"}:
        return "amd64"
    if m in {"aarch64", "arm64"}:
        return "arm64"
    if m in {"armv7l", "armv7"}:
        return "armv7"
    if m in {"armv6l", "armv6"}:
        return "armv6"
    return m or "unknown"


DOCKER_HUB_REGISTRY = "registry-1.docker.io"
DOCKER_HUB_AUTH = "https://auth.docker.io/token"


def _http_get(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, method="GET", headers=headers or {})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        status = int(getattr(resp, "status", 200))
        resp_headers = {k: v for k, v in resp.headers.items()}
        body = resp.read()
        return status, resp_headers, body


def _dockerhub_token(repository: str) -> str:
    params = {"service": "registry.docker.io", "scope": f"repository:{repository}:pull"}
    url = f"{DOCKER_HUB_AUTH}?{urllib.parse.urlencode(params)}"
    status, _, body = _http_get(url)
    if status != 200:
        raise RuntimeError(f"Token request failed for {repository}: HTTP {status}")
    data = json.loads(body.decode("utf-8"))
    token = data.get("token")
    if not token:
        raise RuntimeError(f"Token missing for {repository}")
    return token


def _parse_dockerhub_repository(image: str) -> str:
    if image.count("/") == 0:
        return f"library/{image}"
    return image


def _dockerhub_reference(image: str) -> tuple[str, str]:
    if "@" in image:
        repo, digest = image.split("@", 1)
        return _parse_dockerhub_repository(repo), digest
    if ":" in image.split("/")[-1]:
        repo, tag = image.rsplit(":", 1)
        return _parse_dockerhub_repository(repo), tag
    return _parse_dockerhub_repository(image), "latest"


def _registry_manifest(repository: str, reference: str) -> dict:
    token = _dockerhub_token(repository)
    accept = ", ".join(
        [
            "application/vnd.oci.image.index.v1+json",
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.docker.distribution.manifest.v2+json",
            "application/vnd.oci.image.manifest.v1+json",
        ]
    )
    url = f"https://{DOCKER_HUB_REGISTRY}/v2/{repository}/manifests/{urllib.parse.quote(reference)}"
    status, _, body = _http_get(url, headers={"Authorization": f"Bearer {token}", "Accept": accept})
    if status != 200:
        raise RuntimeError(f"Manifest request failed for {repository}@{reference}: HTTP {status}")
    return json.loads(body.decode("utf-8"))


def _normalize_platform_entry(entry: dict) -> dict:
    p = entry.get("platform") or {}
    os_name = (p.get("os") or "").lower()
    arch = (p.get("architecture") or "").lower()
    variant = (p.get("variant") or "").lower()
    return {"os": os_name, "arch": arch, "variant": variant}


def _platforms_from_manifest(manifest: dict) -> list[dict]:
    media = (manifest.get("mediaType") or "").lower()
    if "manifest.list" in media or "image.index" in media:
        out: list[dict] = []
        for m in manifest.get("manifests", []) or []:
            out.append(_normalize_platform_entry(m))
        return out
    return [{"os": "unknown", "arch": "unknown", "variant": ""}]


def _arch_match(target_arch: str, entry: dict) -> bool:
    if entry.get("os") not in {"linux", "unknown"}:
        return False
    if target_arch == "armv7":
        return entry.get("arch") == "arm" and entry.get("variant") in {"v7", ""}
    if target_arch == "armv6":
        return entry.get("arch") == "arm" and entry.get("variant") in {"v6", ""}
    return entry.get("arch") == target_arch or entry.get("arch") == "unknown"


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    compose_path = os.path.join(repo_root, "docker-compose.yml")
    compose = yaml.safe_load(open(compose_path, "r", encoding="utf-8"))
    images = sorted({svc.get("image", "") for svc in (compose.get("services") or {}).values() if svc.get("image")})

    target_platform = os.environ.get("TARGET_PLATFORM", "").strip().lower()
    if target_platform.startswith("linux/arm/v7"):
        target_arch = "armv7"
    elif target_platform.startswith("linux/arm/v6"):
        target_arch = "armv6"
    elif target_platform.endswith("/arm64"):
        target_arch = "arm64"
    elif target_platform.endswith("/amd64"):
        target_arch = "amd64"
    else:
        target_arch = os.environ.get("TARGET_ARCH", "").strip().lower() or normalize_arch()
    allow_emulation = os.environ.get("ALLOW_AMD64_EMULATION", "false").strip().lower() == "true"

    results: list[dict] = []
    failures: list[dict] = []

    for image in images:
        try:
            if image.startswith("ghcr.io/") or image.startswith("public.ecr.aws/"):
                results.append(
                    {
                        "image": image,
                        "registry": "unsupported",
                        "platforms": [],
                        "target_arch": target_arch,
                        "ok": True,
                        "note": "registry_not_supported_by_checker",
                    }
                )
                continue

            repository, reference = _dockerhub_reference(image)
            manifest = _registry_manifest(repository, reference)
            platforms = _platforms_from_manifest(manifest)
            ok = any(_arch_match(target_arch, p) for p in platforms)
            if not ok and allow_emulation and target_arch != "amd64":
                ok = any(_arch_match("amd64", p) for p in platforms)

            item = {
                "image": image,
                "repository": repository,
                "reference": reference,
                "platforms": platforms,
                "target_platform": target_platform,
                "target_arch": target_arch,
                "allow_amd64_emulation": allow_emulation,
                "ok": ok,
            }
            results.append(item)
            if not ok:
                failures.append(item)
        except Exception as exc:
            failures.append({"image": image, "error": repr(exc), "target_arch": target_arch})
            results.append({"image": image, "error": repr(exc), "target_arch": target_arch, "ok": False})

    reports_dir = os.path.join(repo_root, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    out_path = os.path.join(reports_dir, "image-platforms.json")
    open(out_path, "w", encoding="utf-8", newline="\n").write(json.dumps(results, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
