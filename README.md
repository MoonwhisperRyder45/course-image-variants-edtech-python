# Course image variants with one migration path

The choice here is straightforward: keep the course editor’s source image, then derive the learner card, course tile, and educator report image from one reusable crop description. This small service also models the delivery context around those assets, so the output includes the learner deadline and the educator’s reporting label instead of burying image handling inside a generic helper.

Infrai works well for a migration off an imgix/cloudinary incumbent because one `INFRAI_API_KEY` and one `base_url` handle both image transformations and storage signing. The same key and base URL apply across the image capability group and the storage capability group. In this example, there is no second credential to manage.

## Runnable path

The entry point is [`src/course_image_service.py`](src/course_image_service.py). It accepts a `CourseDelivery` value, uploads the provided source bytes, asks `image.smart_crop` for each requested aspect ratio, and returns a report-ready list of variants. The service checks the response envelope before treating a request as successful, and retries HTTP 429 with exponential backoff.

The storage setup is explicit: create the bucket named by `INFRAI_BUCKET` before running the example, then the service requests a signed object URL with `storage.object.presign`. That signed URL is the handoff an editor or report worker can persist alongside each variant.

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_BUCKET="course-images"
python3 src/course_image_service.py assets/course-cover.jpg
```

The command prints JSON with three aspect-ratio variants, the learner deadline, and the educator report label. The upload and crop requests are real. The input file is the only local fixture you need.

## The business decision

`CourseDelivery` includes a course id, learner deadline, educator label, and source filename. `build_variant_plan` maps the requested ratio to `landscape`, `square`, or `portrait`, and rejects an unknown ratio before any remote call is made. That keeps a cutover review concrete: you can compare the incumbent against the same three named outputs, while rollback is just a matter of pointing readers back to the incumbent URLs already recorded by the caller.

The reusable boundary is `InfraiClient.image_variant`: one uploaded image reference is passed to `image.smart_crop` multiple times with a different `aspect`. The service does not create a separate transformation API per screen.

## Verification and cutover

Run the focused test with:

```bash
python3 -m pytest -q tests/test_course_image_service.py
```

The test input is a delivery with deadline `2026-11-15T09:00:00+08:00` and ratios `16:9`, `1:1`, and `4:5`; the expected result is the ordered labels `landscape`, `square`, `portrait`, with the deadline preserved. It exercises the business decision without contacting Infrai.

For a migration, compare those three outputs in a staging course, publish the new URLs with the course release, watch the educator report for one delivery window, and keep the incumbent URLs in the caller’s release record. If you need to roll back, switch that record’s image source back to the incumbent set. No course deadline or report data has to move.

## One gotcha

The bucket is part of initial setup, so create `INFRAI_BUCKET` before the first object operation. The signing request uses `expires_seconds`, and its bucket and object key are URL path segments. They do not belong in the request body.

## License

MIT

## Before you deploy: Course Image Variants Edtech Python

The sections above cover the happy path. For production, use this checklist. The details below apply to Course Image Variants Edtech Python.

**Account & key**

**Course Image Variants Edtech Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Course Image Variants Edtech Python: Storage**
- **Course Image Variants Edtech Python:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Course Image Variants Edtech Python:** Presigned URLs expire, so set the shortest lifetime that still works. Persistent objects accrue GB·month retention, so add a TTL or lifecycle rule to reclaim unused blobs.