import json
from dataclasses import dataclass
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

type Json = dict[str, Any]


@dataclass(frozen=True)
class ImageReference:
    name: str
    tag: str


@dataclass(frozen=True)
class ImageName:
    namespace: str
    repository: str


def http_get(url: str) -> Json:
    with urlopen(Request(url, headers={"Accept": "application/json"})) as response:
        return json.load(response)


def parse_image_name(image: str) -> ImageName:
    if "/" in image:
        namespace, repository = image.split("/", 1)
    else:
        namespace, repository = "library", image
    return ImageName(namespace=namespace, repository=repository)


def fetch_tag_metadata(image: str, tag: str) -> Json:
    image_name: ImageName = parse_image_name(image)
    return http_get(
        f"https://hub.docker.com/v2/repositories/{image_name.namespace}/{image_name.repository}/tags/{tag}"
    )


def extract_digest(metadata: Json, architecture: str, os: str) -> str | None:
    for entry in metadata.get("images", []):
        if entry["architecture"] == architecture and entry["os"] == os:
            return entry["digest"]
    return None


def get_digest(name: str, tag: str, architecture: str, os: str) -> str:
    try:
        metadata: Json = fetch_tag_metadata(name, tag)
    except HTTPError as exc:
        raise ValueError(f"tag '{tag}' not found ({exc.code})") from exc

    digest: str | None = extract_digest(metadata, architecture, os)
    if digest is None:
        raise ValueError("missing digest information")

    return digest


def check_if_latest(image_ref: ImageReference) -> bool:
    current_digest: str = get_digest(image_ref.name, image_ref.tag, "amd64", "linux")
    latest_digest: str = get_digest(image_ref.name, "latest", "amd64", "linux")

    return current_digest == latest_digest


def iterate_images(filename: str) -> Iterator[ImageReference]:
    with open(filename) as fp:
        for line in fp:
            if not line.strip():
                continue
            try:
                name, tag = line.strip().split(":", 1)
            except ValueError:
                raise ValueError(f"Malformed line in {filename!r}: {line!r}")
            yield ImageReference(name=name, tag=tag)


def find_by_digest(
    image: str, last_digest: str | None = None, page_size: int = 1
) -> set[str]:
    last_digest = (
        get_digest(image, "latest", "amd64", "linux")
        if last_digest is None
        else last_digest
    )
    image_name: ImageName = parse_image_name(image)
    payload: Json = http_get(
        f"https://hub.docker.com/v2/repositories/{image_name.namespace}/{image_name.repository}/tags?page_size={page_size}&ordering=last_updated"
    )

    results: list[Any] | None = payload.get("results")
    if results is None:
        raise ValueError(f"no tags found for '{image}'")

    res: set[str] = set[str]()
    for result in results:
        for image_dict in result["images"]:
            if image_dict["digest"] == last_digest:
                res.add(result["name"])

    return res if len(res) > 0 else find_by_digest(image, last_digest, page_size * 2)


if __name__ == "__main__":
    for image_ref in iterate_images("images.txt"):
        suggested_latest: str = ""
        try:
            is_latest: bool = check_if_latest(image_ref)
            error: str = ""

            if not is_latest:
                candidates: set[str] = find_by_digest(image_ref.name)
                suggested_latest = f"{candidates}"

        except URLError as exc:
            is_latest, error = False, f"network error: {exc.reason}"
        except ValueError as exc:
            is_latest, error = False, str(exc)

        status_icon = "✅" if is_latest else "❌"
        print(
            f"{status_icon} {image_ref.name}:{image_ref.tag} {suggested_latest}", error
        )
