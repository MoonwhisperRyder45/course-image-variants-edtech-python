from src.course_image_service import build_variant_plan


def test_course_delivery_keeps_report_order_for_three_surfaces():
    plan = build_variant_plan(("16:9", "1:1", "4:5"))
    assert [item["label"] for item in plan] == ["landscape", "square", "portrait"]
    assert [item["aspect"] for item in plan] == ["16:9", "1:1", "4:5"]
