import httpx
import pytest
from httpx import SyncByteStream

from travel_briefing.errors import BriefingInputError, BriefingSourceError
from travel_briefing.source_fetch import fetch_newamazing_html


SOURCE_URL = (
    "https://www.newamazing.com.tw/GroupDetail.asp?GroupNo=OSA-SYN-260901"
)


def test_fetcher_uses_one_bounded_get_and_cleans_raw_temp_content(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content="<html><body>合成頁面</body></html>".encode(),
        )

    fetched = fetch_newamazing_html(
        SOURCE_URL,
        transport=httpx.MockTransport(handler),
        temp_parent=tmp_path,
    )

    assert fetched.source_url == SOURCE_URL
    assert fetched.html == "<html><body>合成頁面</body></html>"
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert list(tmp_path.iterdir()) == []


def test_fetcher_allows_only_one_same_host_redirect(tmp_path):
    redirected = (
        "https://www.newamazing.com.tw/print/GroupDetail.asp?"
        "GroupNo=OSA-SYN-260901"
    )
    requests = []

    def handler(request):
        requests.append(str(request.url))
        if len(requests) == 1:
            return httpx.Response(302, headers={"location": redirected})
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"<html>synthetic</html>",
        )

    fetched = fetch_newamazing_html(
        SOURCE_URL,
        transport=httpx.MockTransport(handler),
        temp_parent=tmp_path,
    )

    assert fetched.source_url == redirected
    assert len(requests) == 2


def test_fetcher_rejects_cross_host_redirect_without_second_request(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            302,
            headers={"location": "https://example.invalid/private"},
        )

    with pytest.raises(BriefingInputError, match="redirect"):
        fetch_newamazing_html(
            SOURCE_URL,
            transport=httpx.MockTransport(handler),
            temp_parent=tmp_path,
        )

    assert len(requests) == 1


def test_fetcher_does_not_retry_source_errors_or_accept_oversized_content(tmp_path):
    requests = []

    def unavailable(request):
        requests.append(request)
        return httpx.Response(503, content=b"unavailable")

    with pytest.raises(BriefingSourceError, match="HTTP"):
        fetch_newamazing_html(
            SOURCE_URL,
            transport=httpx.MockTransport(unavailable),
            temp_parent=tmp_path,
        )
    assert len(requests) == 1

    def oversized(_):
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"x" * 33,
        )

    with pytest.raises(BriefingSourceError, match="size limit"):
        fetch_newamazing_html(
            SOURCE_URL,
            transport=httpx.MockTransport(oversized),
            temp_parent=tmp_path,
            max_bytes=32,
        )


def test_fetcher_applies_size_limit_to_streamed_response_bytes(tmp_path):
    class ChunkStream(SyncByteStream):
        def __iter__(self):
            yield b"x" * 20
            yield b"y" * 20

    def handler(_):
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            stream=ChunkStream(),
        )

    with pytest.raises(BriefingSourceError, match="size limit"):
        fetch_newamazing_html(
            SOURCE_URL,
            transport=httpx.MockTransport(handler),
            temp_parent=tmp_path,
            max_bytes=32,
        )

    assert list(tmp_path.iterdir()) == []
