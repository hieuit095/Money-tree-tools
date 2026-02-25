import json
import os
import re
import ssl
import sys
import hashlib
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedImage:
    input_ref: str
    repository: str
    reference: str
    digest: str
    pinned_ref: str


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
    params = {
        "service": "registry.docker.io",
        "scope": f"repository:{repository}:pull",
    }
    url = f"{DOCKER_HUB_AUTH}?{urllib.parse.urlencode(params)}"
    status, _, body = _http_get(url)
    if status != 200:
        raise RuntimeError(f"Token request failed for {repository}: HTTP {status}")
    data = json.loads(body.decode("utf-8"))
    token = data.get("token")
    if not token:
        raise RuntimeError(f"Token missing for {repository}")
    return token


def _parse_dockerhub_ref(image: str) -> tuple[str, str]:
    if "@" in image:
        raise ValueError("Already pinned by digest")
    if image.count("/") == 0:
        repository = f"library/{image}"
    else:
        repository = image
    if ":" in repository.split("/")[-1]:
        repository, tag = repository.rsplit(":", 1)
    else:
        tag = "latest"
    return repository, tag


def resolve_dockerhub_digest(image: str) -> ResolvedImage:
    repository, tag = _parse_dockerhub_ref(image)
    token = _dockerhub_token(repository)
    accept = ", ".join(
        [
            "application/vnd.oci.image.index.v1+json",
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.docker.distribution.manifest.v2+json",
            "application/vnd.oci.image.manifest.v1+json",
        ]
    )
    url = f"https://{DOCKER_HUB_REGISTRY}/v2/{repository}/manifests/{urllib.parse.quote(tag)}"
    status, headers, body = _http_get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
        },
    )
    if status != 200:
        raise RuntimeError(f"Manifest request failed for {image}: HTTP {status}")
    digest = headers.get("Docker-Content-Digest")
    if not digest:
        digest = f"sha256:{hashlib.sha256(body).hexdigest()}"
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError(f"Digest missing/invalid for {image}: {digest!r}")
    pinned = f"{repository}@{digest}"
    return ResolvedImage(
        input_ref=image,
        repository=repository,
        reference=tag,
        digest=digest,
        pinned_ref=pinned,
    )


def _replace_image_refs_in_compose(compose_text: str, replacements: dict[str, str]) -> str:
    def repl(match: re.Match) -> str:
        prefix = match.group(1)
        original = match.group(2).strip()
        return f"{prefix}{replacements.get(original, original)}"

    return re.sub(r"(^\s*image:\s*)([^\s#]+)\s*$", repl, compose_text, flags=re.MULTILINE)


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    compose_path = os.path.join(repo_root, "docker-compose.yml")
    if not os.path.exists(compose_path):
        raise RuntimeError(f"docker-compose.yml not found: {compose_path}")

    compose_text = open(compose_path, "r", encoding="utf-8").read()
    images = sorted(set(re.findall(r"^\s*image:\s*([^\s#]+)\s*$", compose_text, flags=re.MULTILINE)))

    resolved: list[ResolvedImage] = []
    replacements: dict[str, str] = {}
    errors: list[dict[str, str]] = []
    for image in images:
        if "@" in image:
            repo, digest = image.split("@", 1)
            resolved.append(
                ResolvedImage(
                    input_ref=image,
                    repository=repo,
                    reference="digest",
                    digest=digest,
                    pinned_ref=image,
                )
            )
            continue
        try:
            resolved_img = resolve_dockerhub_digest(image)
            resolved.append(resolved_img)
            replacements[image] = resolved_img.pinned_ref
        except Exception as exc:
            errors.append({"image": image, "error": repr(exc)})

    updated_text = _replace_image_refs_in_compose(compose_text, replacements)
    if updated_text != compose_text:
        open(compose_path, "w", encoding="utf-8", newline="\n").write(updated_text)

    reports_dir = os.path.join(repo_root, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    out_path = os.path.join(reports_dir, "image-digests.json")
    open(out_path, "w", encoding="utf-8", newline="\n").write(
        json.dumps([r.__dict__ for r in resolved], indent=2, sort_keys=True)
    )

    if errors:
        open(os.path.join(reports_dir, "image-digests.errors.json"), "w", encoding="utf-8", newline="\n").write(
            json.dumps(errors, indent=2, sort_keys=True)
        )
        return 1

    err_marker = os.path.join(reports_dir, "image-digests.error.txt")
    if os.path.exists(err_marker):
        os.remove(err_marker)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reports_dir = os.path.join(repo_root, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        open(os.path.join(reports_dir, "image-digests.error.txt"), "w", encoding="utf-8").write(repr(exc))
        raise
