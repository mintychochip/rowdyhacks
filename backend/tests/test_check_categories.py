from app.checks.interface import CheckCategory


def test_cross_hackathon_category_exists():
    assert hasattr(CheckCategory, "CROSS_HACKATHON")
    assert CheckCategory.CROSS_HACKATHON == "cross_hackathon"


def test_repeat_offender_category_exists():
    assert hasattr(CheckCategory, "REPEAT_OFFENDER")
    assert CheckCategory.REPEAT_OFFENDER == "repeat_offender"
