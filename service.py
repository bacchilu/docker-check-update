from dataclasses import dataclass
from typing import Any, Protocol

type Json = dict[str, Any]

ARCHITECTURE, OS = "amd64", "linux"


class DockerHubError(Exception):
    pass


class DockerHubAPIProtocol(Protocol):
    @staticmethod
    def fetch_tag_metadata(image: str, tag: str) -> Json: ...

    @staticmethod
    def fetch_tags_page(image: str, page_size: int) -> Json: ...


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


def get_digest(name: str, tag: str, docker_hub_api: DockerHubAPIProtocol) -> str:
    metadata: Json = docker_hub_api.fetch_tag_metadata(name, tag)
    digest: str | None = extract_digest(metadata)
    if digest is None:
        raise ValueError("missing digest information")

    return digest


class DockerImageUpdateService:
    def __init__(self, docker_hub_api: DockerHubAPIProtocol):
        self.docker_hub_api: DockerHubAPIProtocol = docker_hub_api

    def check_if_latest(self, image_ref: ImageReference) -> bool:
        current_digest: str = get_digest(
            image_ref.name, image_ref.tag, self.docker_hub_api
        )
        latest_digest: str = get_digest(image_ref.name, "latest", self.docker_hub_api)

        return current_digest == latest_digest

    def find_by_digest(
        self, image: str, last_digest: str | None = None, page_size: int = 1
    ) -> set[str]:
        last_digest = (
            get_digest(image, "latest", self.docker_hub_api)
            if last_digest is None
            else last_digest
        )
        payload: Json = self.docker_hub_api.fetch_tags_page(image, page_size)

        results: list[Any] | None = payload.get("results")
        if results is None:
            raise ValueError(f"no tags found for '{image}'")

        res: set[str] = set[str]()
        for result in results:
            for image_dict in result["images"]:
                if image_dict["digest"] == last_digest:
                    res.add(result["name"])

        return (
            res
            if len(res) > 0
            else DockerImageUpdateService.find_by_digest(
                self, image, last_digest, page_size * 2
            )
        )
