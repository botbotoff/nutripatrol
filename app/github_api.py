"""Read the GitHub issues linked to tickets.

Moderators open issues on openfoodfacts/openfoodfacts-server themselves, for
a problem that comes from how Open Food Facts computes something, and link
them to the ticket. NutriPatrol only reads them, to show their state.

Every call is best effort: GitHub being slow, down, or rate limiting us must
not break a ticket page, so failures are logged and reported as `None`.
"""

import logging
import re
from typing import NamedTuple

import requests

from app.config import settings

logger = logging.getLogger(__name__)

#: The only repository issues can be linked from.
ISSUE_REPOSITORY = "openfoodfacts/openfoodfacts-server"

ISSUE_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?github\.com/openfoodfacts/openfoodfacts-server"
    r"/issues/(?P<number>[1-9][0-9]*)/?(?:[?#].*)?$",
    re.IGNORECASE,
)

TIMEOUT_SECONDS = 5


class IssueNotFound(Exception):
    """GitHub answered that the issue does not exist."""


class GitHubIssue(NamedTuple):
    number: int
    title: str | None
    state: str | None
    state_reason: str | None


def parse_issue_url(url: str) -> int | None:
    """The issue number of an openfoodfacts-server issue URL, else None."""
    match = ISSUE_URL_PATTERN.match(url.strip())
    return int(match["number"]) if match else None


def issue_url(number: int) -> str:
    return f"https://github.com/{ISSUE_REPOSITORY}/issues/{number}"


def fetch_issue(number: int) -> GitHubIssue | None:
    """Read an issue from GitHub.

    Raises IssueNotFound when GitHub says there is no such issue (a pull
    request, which shares the numbering, counts as none). Returns None when
    GitHub could not tell.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    try:
        response = requests.get(
            f"https://api.github.com/repos/{ISSUE_REPOSITORY}/issues/{number}",
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("Could not reach GitHub for issue %s: %s", number, exc)
        return None
    if response.status_code in (404, 410):
        raise IssueNotFound(number)
    if not response.ok:
        logger.warning(
            "GitHub answered %s for issue %s: %s",
            response.status_code,
            number,
            response.text[:200],
        )
        return None
    data = response.json()
    if "pull_request" in data:
        raise IssueNotFound(number)
    return GitHubIssue(
        number=number,
        title=data.get("title"),
        state=data.get("state"),
        state_reason=data.get("state_reason"),
    )
