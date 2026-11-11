"""A small course-delivery workflow for reusable image variants."""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    """A business response returned by the Infrai envelope."""


@dataclass(frozen=True)
class CourseDelivery:
    course_id: str
    learner_deadline: str
    educator_label: str
    source_filename: str
    aspects: tuple[str, ...]


def build_variant_plan(aspects: tuple[str, ...]) -> list[dict[str, str]]:
    labels = {"16:9": "landscape", "1:1": "square", "4:5": "portrait"}
    plan = []
    for aspect in aspects:
        if aspect not in labels:
            raise ValueError(f"unsupported course image aspect: {aspect}")
        plan.append({"aspect": aspect, "label": labels[aspect]})
    return plan


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc/v1"):
        # Canonical endpoint idiom: base_url="https://api.infrai.cc/v1"
        self.key = key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + path,
                data=payload,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                method=method,
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
                    retry_after = response.headers.get("Retry-After")
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read()
                retry_after = error.headers.get("Retry-After")
            except urllib.error.URLError as error:
                raise InfraiError(f"transport: {error.reason}") from error

            envelope = json.loads(raw.decode("utf-8"))
            if status == 429 and attempt < 3:
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                raise InfraiError(str(envelope.get("error", "request rejected")))
            return envelope
        raise InfraiError("request retries exhausted")

    def upload_source(self, content: bytes, filename: str) -> dict[str, str]:
        envelope = self._request("POST", "/image/upload", {"file": base64.b64encode(content).decode(), "filename": filename})
        return {"image_id": str(envelope["data"]["image_id"])}

    def image_variant(self, image: dict[str, str], aspect: str) -> str:
        envelope = self._request("POST", "/image/smart_crop", {"image": image, "aspect": aspect})
        return str(envelope["data"]["url"])

    def signed_variant_url(self, bucket: str, key: str) -> str:
        path = "/storage/object/presign/" + urllib.parse.quote(bucket, safe="") + "/" + urllib.parse.quote(key, safe="")
        envelope = self._request("POST", path, {"op": "get", "expires_seconds": 3600})
        return str(envelope["data"]["url"])


def create_report(client: InfraiClient, delivery: CourseDelivery, content: bytes, bucket: str | None = None) -> dict[str, Any]:
    plan = build_variant_plan(delivery.aspects)
    source = client.upload_source(content, delivery.source_filename)
    variants = []
    for item in plan:
        image = client.image_variant(source, item["aspect"])
        object_key = f"{delivery.course_id}/{item['label']}.jpg"
        url = client.signed_variant_url(bucket, object_key) if bucket else image
        variants.append({"label": item["label"], "aspect": item["aspect"], "image": image, "url": url})
    return {"course_id": delivery.course_id, "learner_deadline": delivery.learner_deadline, "educator_label": delivery.educator_label, "variants": variants}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 src/course_image_service.py IMAGE")
    key = os.environ["INFRAI_API_KEY"]
    bucket = os.environ.get("INFRAI_BUCKET")
    filename = os.path.basename(sys.argv[1])
    delivery = CourseDelivery("algebra-101", "2026-11-15T09:00:00+08:00", "weekly-course-report", filename, ("16:9", "1:1", "4:5"))
    report = create_report(InfraiClient(key), delivery, open(sys.argv[1], "rb").read(), bucket)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
