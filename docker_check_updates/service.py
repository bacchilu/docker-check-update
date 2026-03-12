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


class DockerImageUpdateService:
    def __init__(self, docker_hub_api: DockerHubAPIProtocol):
        self.docker_hub_api: DockerHubAPIProtocol = docker_hub_api

    def _get_digest(self, name: str, tag: str) -> str:
        metadata: Json = self.docker_hub_api.fetch_tag_metadata(name, tag)
        digest: str | None = extract_digest(metadata)
        if digest is None:
            raise ValueError("missing digest information")
        return digest

    def _get_tags(self, current_digest: str, image: str, page_size: int) -> set[str]:
        payload: Json = self.docker_hub_api.fetch_tags_page(image, page_size)
        results: list[Any] | None = payload.get("results")
        if results is None:
            raise ValueError(f"no tags found for '{image}'")

        res: set[str] = set[str]()
        for result in results:
            for image_dict in result["images"]:
                if image_dict["digest"] == current_digest:
                    res.add(result["name"])

        return res

    def check_if_latest(self, image_ref: ImageReference) -> bool:
        current_digest: str = self._get_digest(image_ref.name, image_ref.tag)
        latest_digest: str = self._get_digest(image_ref.name, "latest")

        return current_digest == latest_digest

    def find_latests_tags_by_digest(
        self, image: str, last_digest: str | None = None, page_size: int = 1
    ) -> set[str]:
        current_digest: str = (
            self._get_digest(image, "latest") if last_digest is None else last_digest
        )
        tags: set[str] = self._get_tags(current_digest, image, page_size)
        return (
            tags
            if len(tags) > 0
            else DockerImageUpdateService.find_latests_tags_by_digest(
                self, image, current_digest, page_size * 2
            )
        )
