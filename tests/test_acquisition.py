import pytest

from youtube_rag.acquisition import CaptionAcquisitionError, resolve_video_id


@pytest.mark.parametrize("value", [
    "b76rDd9FYeY",
    "https://www.youtube.com/watch?v=b76rDd9FYeY",
    "https://youtu.be/b76rDd9FYeY?t=10",
])
def test_resolve_video_id(value):
    assert resolve_video_id(value) == "b76rDd9FYeY"


def test_rejects_non_youtube_or_malformed_id():
    with pytest.raises(CaptionAcquisitionError):
        resolve_video_id("https://example.com/watch?v=b76rDd9FYeY")
    with pytest.raises(CaptionAcquisitionError):
        resolve_video_id("https://www.youtube.com/watch?v=short")
