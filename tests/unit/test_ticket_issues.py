"""Tests for the GitHub issues moderators link to tickets.

The issue lives on openfoodfacts/openfoodfacts-server and is opened by the
moderator; NutriPatrol records the link, and reads the issue's state from
GitHub, best effort. GitHub is never called here: `fetch_issue` is replaced
by a stub the tests control.
"""

import asyncio
from datetime import datetime, timedelta

import httpx
import pytest
from peewee import SqliteDatabase

from app import api as api_module
from app.api import app
from app.github_api import GitHubIssue, IssueNotFound, parse_issue_url
from app.middleware import auth as auth_module
from app.models import (
    FlagModel,
    ModeratorActionModel,
    TicketCommentModel,
    TicketIssueModel,
    TicketModel,
)

BARCODE = "3017620422003"
ISSUE_URL = "https://github.com/openfoodfacts/openfoodfacts-server/issues/1234"
MODELS = [
    TicketModel,
    FlagModel,
    TicketIssueModel,
    ModeratorActionModel,
    TicketCommentModel,
]


@pytest.fixture
def database(tmp_path, monkeypatch):
    """Run the endpoints against a throwaway SQLite database."""
    test_db = SqliteDatabase(str(tmp_path / "nutripatrol.db"))
    test_db.bind(MODELS)
    test_db.create_tables(MODELS)
    test_db.close()
    monkeypatch.setattr(api_module, "db", test_db)
    yield test_db
    test_db.close()


@pytest.fixture
def github(monkeypatch):
    """Stand in for GitHub: a dict of issue number -> what GitHub answers.

    A GitHubIssue is returned, IssueNotFound raised, and None means GitHub
    could not be reached. Numbers absent from the dict are not found. Every
    call is recorded in `calls`.
    """
    answers = {}
    calls = []

    def fetch(number):
        calls.append(number)
        answer = answers.get(number, IssueNotFound(number))
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(api_module, "fetch_issue", fetch)
    answers[1234] = GitHubIssue(1234, "Nutri-Score is wrong for water", "open", None)
    return type("GitHub", (), {"answers": answers, "calls": calls})


@pytest.fixture
def act_as(monkeypatch):
    """Answer the auth server as whoever the test is currently acting as."""
    current = {"user_id": "a-moderator", "moderator": 1}

    async def user_data(session_cookie, auth_base_url):
        return {
            "user_id": current["user_id"],
            "user": {"moderator": current["moderator"]},
        }

    monkeypatch.setattr(auth_module, "_get_user_data_cached", user_data)

    def switch(user_id, moderator=0):
        current.update(user_id=user_id, moderator=moderator)

    return switch


def request(method, url, json=None):
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            cookies={"session": "a-session-cookie"},
        ) as client:
            return await client.request(method, url, json=json)

    return asyncio.run(send())


def make_ticket(flagged_by="alice"):
    ticket = TicketModel.create(
        barcode=BARCODE,
        type="product",
        url=f"https://world.openfoodfacts.org/product/{BARCODE}",
        status="open",
        flavor="off",
        created_at=datetime.utcnow(),
    )
    FlagModel.create(
        ticket=ticket,
        barcode=BARCODE,
        type="product",
        url=ticket.url,
        user_id=flagged_by,
        device_id="a-device",
        source="web",
        flavor="off",
        reason="nutriscore",
        created_at=datetime.utcnow(),
    )
    return ticket


def link(ticket_id, url=ISSUE_URL):
    return request("POST", f"/api/v1/tickets/{ticket_id}/issues", {"url": url})


@pytest.mark.parametrize(
    "url,number",
    [
        (ISSUE_URL, 1234),
        (ISSUE_URL + "/", 1234),
        (ISSUE_URL + "#issuecomment-1", 1234),
        ("  https://www.github.com/OpenFoodFacts/openfoodfacts-server/issues/7 ", 7),
        ("https://github.com/openfoodfacts/openfoodfacts-server/pull/1234", None),
        ("https://github.com/openfoodfacts/robotoff/issues/1234", None),
        ("https://github.com/openfoodfacts/openfoodfacts-server/issues/0", None),
        ("https://example.com/openfoodfacts/openfoodfacts-server/issues/1", None),
        ("#1234", None),
    ],
)
def test_parse_issue_url(url, number):
    assert parse_issue_url(url) == number


def test_linking_an_issue_records_it_with_its_state(database, github, act_as):
    ticket = make_ticket()

    response = link(ticket.id)

    assert response.status_code == 200, response.text
    issue = response.json()
    assert issue["number"] == 1234
    assert issue["url"] == ISSUE_URL
    assert issue["title"] == "Nutri-Score is wrong for water"
    assert issue["state"] == "open"
    assert issue["user_id"] == "a-moderator"
    action = ModeratorActionModel.get()
    assert (action.action_type, action.issue_id) == ("issue_linked", issue["id"])


def test_linking_a_linked_issue_again_records_nothing(database, github, act_as):
    ticket = make_ticket()
    first = link(ticket.id).json()

    response = link(ticket.id, ISSUE_URL + "#issuecomment-1")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == first["id"]
    assert ModeratorActionModel.select().count() == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/openfoodfacts/robotoff/issues/1",
        "https://github.com/openfoodfacts/openfoodfacts-server/pull/1234",
        "not a url",
    ],
)
def test_only_openfoodfacts_server_issues_are_linked(database, github, act_as, url):
    ticket = make_ticket()

    response = link(ticket.id, url)

    assert response.status_code == 422
    assert TicketIssueModel.select().count() == 0


def test_an_issue_github_does_not_know_is_refused(database, github, act_as):
    ticket = make_ticket()

    response = link(
        ticket.id, "https://github.com/openfoodfacts/openfoodfacts-server/issues/99"
    )

    assert response.status_code == 422
    assert "not found" in response.json()["detail"]
    assert ModeratorActionModel.select().count() == 0


def test_an_issue_is_linked_even_when_github_is_down(database, github, act_as):
    ticket = make_ticket()
    github.answers[1234] = None

    response = link(ticket.id)

    assert response.status_code == 200, response.text
    assert response.json()["state"] is None
    assert response.json()["checked_at"] is None


def test_only_moderators_link_and_unlink_issues(database, github, act_as):
    ticket = make_ticket(flagged_by="alice")
    issue_id = link(ticket.id).json()["id"]
    act_as("alice")

    assert link(ticket.id).status_code == 403
    response = request("DELETE", f"/api/v1/tickets/{ticket.id}/issues/{issue_id}")
    assert response.status_code == 403


def test_linking_to_an_unknown_ticket_is_a_404(database, github, act_as):
    assert link(999).status_code == 404


def test_unlinking_keeps_the_issue_for_the_history(database, github, act_as):
    ticket = make_ticket()
    issue_id = link(ticket.id).json()["id"]

    response = request("DELETE", f"/api/v1/tickets/{ticket.id}/issues/{issue_id}")

    assert response.status_code == 200, response.text
    assert response.json()["removed_at"] is not None
    assert request("GET", f"/api/v1/tickets/{ticket.id}/issues").json() == {
        "issues": []
    }
    actions = request("GET", f"/api/v1/tickets/{ticket.id}/actions").json()
    assert [(a["action_type"], a["issue"]["number"]) for a in actions["actions"]] == [
        ("issue_unlinked", 1234),
        ("issue_linked", 1234),
    ]


def test_unlinking_an_issue_twice_is_a_404(database, github, act_as):
    ticket = make_ticket()
    issue_id = link(ticket.id).json()["id"]
    request("DELETE", f"/api/v1/tickets/{ticket.id}/issues/{issue_id}")

    response = request("DELETE", f"/api/v1/tickets/{ticket.id}/issues/{issue_id}")

    assert response.status_code == 404


def test_relinking_an_unlinked_issue_brings_it_back(database, github, act_as):
    ticket = make_ticket()
    issue_id = link(ticket.id).json()["id"]
    request("DELETE", f"/api/v1/tickets/{ticket.id}/issues/{issue_id}")

    response = link(ticket.id)

    assert response.status_code == 200, response.text
    assert response.json()["id"] == issue_id
    assert response.json()["removed_at"] is None
    assert [a.action_type for a in ModeratorActionModel.select()] == [
        "issue_linked",
        "issue_unlinked",
        "issue_linked",
    ]


def test_the_flagger_reads_the_issues_but_no_one_else(database, github, act_as):
    ticket = make_ticket(flagged_by="alice")
    link(ticket.id)

    act_as("alice")
    response = request("GET", f"/api/v1/tickets/{ticket.id}/issues")
    assert response.status_code == 200, response.text
    assert [i["number"] for i in response.json()["issues"]] == [1234]

    act_as("bob")
    assert request("GET", f"/api/v1/tickets/{ticket.id}/issues").status_code == 404


def test_a_stale_state_is_refreshed_from_github(database, github, act_as):
    ticket = make_ticket()
    issue_id = link(ticket.id).json()["id"]
    TicketIssueModel.update(checked_at=datetime.utcnow() - timedelta(hours=1)).where(
        TicketIssueModel.id == issue_id
    ).execute()
    github.answers[1234] = GitHubIssue(1234, "Fixed", "closed", "completed")

    response = request("GET", f"/api/v1/tickets/{ticket.id}/issues")

    [issue] = response.json()["issues"]
    assert (issue["title"], issue["state"], issue["state_reason"]) == (
        "Fixed",
        "closed",
        "completed",
    )
    assert TicketIssueModel.get_by_id(issue_id).state == "closed"


def test_a_fresh_state_is_not_asked_again(database, github, act_as):
    ticket = make_ticket()
    link(ticket.id)
    calls = len(github.calls)

    request("GET", f"/api/v1/tickets/{ticket.id}/issues")

    assert len(github.calls) == calls


def test_a_state_github_could_not_give_is_asked_again(database, github, act_as):
    ticket = make_ticket()
    github.answers[1234] = None
    link(ticket.id)
    github.answers[1234] = GitHubIssue(1234, "Water", "open", None)

    response = request("GET", f"/api/v1/tickets/{ticket.id}/issues")

    assert response.json()["issues"][0]["state"] == "open"


def test_tickets_carry_their_issues_without_calling_github(database, github, act_as):
    with_issue = make_ticket()
    make_ticket()
    link(with_issue.id)
    calls = len(github.calls)

    response = request("GET", "/api/v1/tickets")

    assert response.status_code == 200, response.text
    issues = {t["id"]: t["issues"] for t in response.json()["tickets"]}
    assert [i["number"] for i in issues[with_issue.id]] == [1234]
    assert issues[with_issue.id + 1] == []
    assert len(github.calls) == calls


class FakeResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._data = data or {}
        self.text = str(self._data)

    def json(self):
        return self._data


@pytest.fixture
def github_http(monkeypatch):
    """Replace the HTTP call of fetch_issue; `answer` is what it gets."""
    from app import github_api

    state = {"answer": FakeResponse(200, {}), "headers": None}

    def get(url, headers, timeout):
        state["headers"] = headers
        if isinstance(state["answer"], Exception):
            raise state["answer"]
        return state["answer"]

    monkeypatch.setattr(github_api.requests, "get", get)
    return state


def test_fetch_issue_reads_title_and_state(github_http):
    from app.github_api import fetch_issue

    github_http["answer"] = FakeResponse(
        200, {"title": "Water", "state": "closed", "state_reason": "not_planned"}
    )

    assert fetch_issue(5) == GitHubIssue(5, "Water", "closed", "not_planned")
    assert "Authorization" not in github_http["headers"]


def test_fetch_issue_sends_the_token_when_there_is_one(github_http, monkeypatch):
    from app import github_api

    monkeypatch.setattr(github_api.settings, "github_token", "a-token")

    github_api.fetch_issue(5)

    assert github_http["headers"]["Authorization"] == "Bearer a-token"


@pytest.mark.parametrize(
    "answer",
    [FakeResponse(404), FakeResponse(200, {"title": "A PR", "pull_request": {}})],
    ids=["missing", "pull-request"],
)
def test_fetch_issue_reports_what_is_not_an_issue(github_http, answer):
    from app.github_api import fetch_issue

    github_http["answer"] = answer

    with pytest.raises(IssueNotFound):
        fetch_issue(5)


@pytest.mark.parametrize(
    "answer",
    [FakeResponse(403, {"message": "rate limited"}), FakeResponse(502)],
    ids=["rate-limited", "server-error"],
)
def test_fetch_issue_returns_none_when_github_cannot_tell(github_http, answer):
    from app.github_api import fetch_issue

    github_http["answer"] = answer

    assert fetch_issue(5) is None


def test_fetch_issue_returns_none_when_github_is_unreachable(github_http):
    import requests

    from app.github_api import fetch_issue

    github_http["answer"] = requests.ConnectionError("down")

    assert fetch_issue(5) is None
