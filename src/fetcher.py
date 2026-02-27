from curl_cffi import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from config import TRUST_HEADERS


def is_transient_error(exception: Exception) -> bool:
    """Determine whether an exception should trigger a retry."""
    if isinstance(exception, requests.exceptions.HTTPError):
        response = exception.response
        if response and response.status_code in {403, 503}:
            return True
    return False


@retry(
    retry=retry_if_exception(is_transient_error),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(5),
)
def fetch_html(url: str) -> str:
    """Retrieve the HTML body for a provided URL."""
    response = requests.get(
        url,
        timeout=30,
        allow_redirects=True,
        impersonate="safari15_5",
        headers=TRUST_HEADERS,
    )
    response.raise_for_status()
    return response.text
