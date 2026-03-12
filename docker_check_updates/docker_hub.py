import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .service import DockerHubAPIProtocol, DockerHubError, Json


@dataclass(frozen=True)
class ImageName:
    namespace: str
    repository: str

    @staticmethod
    def parse(image: str) -> "ImageName":
        if "/" in image:
            namespace, repository = image.split("/", 1)
        else:
            namespace, repository = "library", image
        return ImageName(namespace=namespace, repository=repository)


class DockerHubAPI(DockerHubAPIProtocol):
    @staticmethod
    def _http_get(url: str, resource: str) -> Json:
        try:
            with urlopen(
                Request(url, headers={"Accept": "application/json"})
            ) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code == 404:
                raise DockerHubError(f"{resource} not found ({exc.code})") from exc
            raise DockerHubError(f"{resource} request failed ({exc.code})") from exc
        except URLError as exc:
            raise DockerHubError(f"network error: {exc.reason}") from exc

    @staticmethod
    def fetch_tag_metadata(image: str, tag: str) -> Json:
        image_name: ImageName = ImageName.parse(image)
        return DockerHubAPI._http_get(
            f"https://hub.docker.com/v2/repositories/{image_name.namespace}/{image_name.repository}/tags/{tag}",
            f"tag '{tag}'",
        )

    @staticmethod
    def fetch_tags_page(image: str, page_size: int) -> Json:
        image_name: ImageName = ImageName.parse(image)
        return DockerHubAPI._http_get(
            f"https://hub.docker.com/v2/repositories/{image_name.namespace}/{image_name.repository}/tags?page_size={page_size}&ordering=last_updated",
            f"repository '{image}' tags",
        )
