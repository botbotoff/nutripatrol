"""Who may read which flags and tickets.

The whole rule lives here: a moderator reads every flag and every ticket;
anyone else reads the flags they raised themselves, and the tickets those
flags are attached to.

A ticket gathers the flags of everyone who reported the same product or
image, so following one's own ticket must not hand over the others' flags:
the two are separate questions, answered by `visible_flags` and
`visible_tickets`.

Every endpoint that reads flags or tickets on behalf of a user starts from
one of these queries, and narrows it further with its own filters and
pagination. Each `.where()` added to them is ANDed with the rule, so no
filter can widen what a user sees.
"""

from fastapi import HTTPException
from peewee import ModelSelect

from app.middleware.auth import AuthenticatedUser
from app.models import FlagModel, TicketModel


def visible_flags(user: AuthenticatedUser) -> ModelSelect:
    """The flags `user` may read: all of them for a moderator, else their own.

    A flag with no author (empty or null `user_id`) is no one's own: it is
    left to the moderators, rather than handed to a session whose auth
    server answered without a user id.
    """
    if user.is_moderator:
        return FlagModel.select()
    return FlagModel.select().where(
        FlagModel.user_id == user.user_id,
        FlagModel.user_id != "",
        FlagModel.user_id.is_null(False),
    )


def visible_tickets(user: AuthenticatedUser) -> ModelSelect:
    """The tickets `user` may read: all of them for a moderator, else the
    ones one of their own flags is attached to."""
    if user.is_moderator:
        return TicketModel.select()
    return TicketModel.select().where(
        TicketModel.id.in_(visible_flags(user).select(FlagModel.ticket))
    )


def get_visible_ticket_or_404(user: AuthenticatedUser, ticket_id: int) -> TicketModel:
    """The ticket, if `user` may read it.

    404 both when it does not exist and when it is someone else's: which
    products other users have reported is not something a flagger gets to
    probe for.
    """
    ticket = visible_tickets(user).where(TicketModel.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Not found")
    return ticket
