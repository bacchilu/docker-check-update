# Docker Check Updates

Small Python CLI that reads Docker image references from `images.txt`, checks whether each pinned tag still matches Docker Hub's `latest`, and tries to suggest an updated tag when it does not.

## What it does

Given a file like:

```text
nginx:1.29.5
python:3.14.3
opensearchproject/opensearch:3.5.0
```

the script:

1. Parses each `image:tag` entry from `images.txt`.
2. Fetches Docker Hub metadata for the pinned tag and for `latest`.
3. Compares the `linux/amd64` image digests.
4. Prints whether the pinned tag is already up to date.
5. If not, looks through recently updated tags and suggests tags that share the same digest as `latest`.

## How suggestions work

The project does not guess version numbers. It uses image digests:

- If your pinned tag has the same digest as `latest`, it is treated as current.
- If it differs, the script searches Docker Hub tags and returns the tag names that currently point to the same digest as `latest`.

This means the suggestion is based on what Docker Hub currently publishes, not on semantic version ordering.

## Requirements

- Python 3
- Network access to `hub.docker.com`

No Docker daemon is required because the script only uses the Docker Hub HTTP API.

## Project layout

The Python code lives in the `docker_check_updates/` package:

```text
docker_check_updates/
  __init__.py
  __main__.py
  main.py
  service.py
  docker_hub.py
```

`images.txt` stays at the repository root as the default input file.

## Usage

Run the checker from the repository root with:

```bash
python3 -m docker_check_updates
```

## Input format

Add one Docker image per line in `images.txt`:

```text
image:tag
namespace/image:tag
```

Examples:

```text
nginx:1.29.6
rabbitmq:4.2.4
bacchilu/static-server:3.0.9
```

Blank lines are ignored. Invalid lines raise an error.

## Example output

```text
✅ nginx:1.29.6
❌ nginx:1.29.5 {'1.29.6'}
```

## Notes

- Official Docker Hub images without a namespace are resolved under `library/`.
- The comparison is currently limited to `linux/amd64`.
- Some repositories may not publish a `latest` tag.
- Suggestions can contain more than one tag if multiple tags share the same digest.
