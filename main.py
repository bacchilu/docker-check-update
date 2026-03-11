from typing import Iterator

from docker_hub import DockerHubError
from service import ImageReference, check_if_latest, find_by_digest


def iterate_images(filename: str) -> Iterator[ImageReference]:
    with open(filename) as fp:
        for line in fp:
            if not line.strip():
                continue
            try:
                yield ImageReference.parse(line)
            except ValueError as exc:
                raise ValueError(f"Malformed line in {filename!r}: {line!r}") from exc


if __name__ == "__main__":
    for image_ref in iterate_images("images.txt"):
        suggested_latest: str = ""
        try:
            is_latest: bool = check_if_latest(image_ref)
            error: str = ""

            if not is_latest:
                candidates: set[str] = find_by_digest(image_ref.name)
                suggested_latest = f"{candidates}"

        except DockerHubError as exc:
            is_latest, error = False, str(exc)
        except ValueError as exc:
            is_latest, error = False, str(exc)

        status_icon = "✅" if is_latest else "❌"
        print(
            f"{status_icon} {image_ref.name}:{image_ref.tag} {suggested_latest}", error
        )
