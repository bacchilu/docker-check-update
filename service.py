from dataclasses import dataclass
from typing import Any

from docker_hub import DockerHubAPI

type Json = dict[str, Any]

ARCHITECTURE, OS = "amd64", "linux"


@dataclass(frozen=True)
class ImageReference:
    name: str
    tag: str

    @staticmethod
    def parse(line: str) -> "ImageReference":
        try:
            name, tag = line.strip().split(":", 1)
        except ValueError as exc:
            raise ValueError(f"Malformed image reference: {line!r}") from exc
        return ImageReference(name=name, tag=tag)


def extract_digest(metadata: Json) -> str | None:
    for entry in metadata.get("images", []):
        if entry["architecture"] == ARCHITECTURE and entry["os"] == OS:
            return entry["digest"]
    return None


def get_digest(name: str, tag: str) -> str:
    metadata: Json = DockerHubAPI.fetch_tag_metadata(name, tag)
    digest: str | None = extract_digest(metadata)
    if digest is None:
        raise ValueError("missing digest information")

    return digest


def check_if_latest(image_ref: ImageReference) -> bool:
    current_digest: str = get_digest(image_ref.name, image_ref.tag)
    latest_digest: str = get_digest(image_ref.name, "latest")

    return current_digest == latest_digest


def find_by_digest(
    image: str, last_digest: str | None = None, page_size: int = 1
) -> set[str]:
    last_digest = get_digest(image, "latest") if last_digest is None else last_digest
    payload: Json = DockerHubAPI.fetch_tags_page(image, page_size)

    results: list[Any] | None = payload.get("results")
    if results is None:
        raise ValueError(f"no tags found for '{image}'")

    res: set[str] = set[str]()
    for result in results:
        for image_dict in result["images"]:
            if image_dict["digest"] == last_digest:
                res.add(result["name"])

    return res if len(res) > 0 else find_by_digest(image, last_digest, page_size * 2)
