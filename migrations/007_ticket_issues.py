"""Peewee migrations -- 007_ticket_issues.py."""

import peewee as pw
from peewee_migrate import Migrator


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    @migrator.create_model
    class TicketIssueModel(pw.Model):
        id = pw.AutoField()
        ticket = pw.ForeignKeyField(
            column_name="ticket_id",
            field="id",
            model=migrator.orm["tickets"],
            index=True,
        )
        number = pw.IntegerField()
        url = pw.TextField()
        title = pw.TextField(null=True)
        state = pw.CharField(max_length=20, null=True)
        state_reason = pw.CharField(max_length=20, null=True)
        checked_at = pw.DateTimeField(null=True)
        user_id = pw.TextField()
        created_at = pw.DateTimeField()
        removed_at = pw.DateTimeField(null=True)

        class Meta:
            table_name = "ticket_issues"
            indexes = ((("ticket", "number"), True),)

    migrator.add_fields(
        "moderator_actions",
        issue=pw.ForeignKeyField(
            column_name="issue_id",
            field="id",
            model=migrator.orm["ticket_issues"],
            null=True,
        ),
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    # Postgres drops the foreign key's index with the column, but drop it
    # explicitly so that the rollback also works on SQLite.
    migrator.drop_index("moderator_actions", "issue")
    migrator.remove_fields("moderator_actions", "issue")
    migrator.remove_model("ticket_issues")
