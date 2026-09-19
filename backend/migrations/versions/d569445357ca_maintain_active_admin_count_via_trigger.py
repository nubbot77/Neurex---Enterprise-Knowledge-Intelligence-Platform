"""maintain active_admin_count via trigger

Revision ID: d569445357ca
Revises: 8839e1aa9553
Create Date: 2026-09-19 12:05:10.194723

Enforces the admin range from architecture §7.7: an active organization holds at least
one and at most ``max_admins`` active admins.

Split across two mechanisms because the two ends of the range are not symmetrical:

* The **ceiling** is the CHECK constraint already on ``organizations``. It can be
  declarative because exceeding it is never legitimate, not even briefly.
* The **floor** lives here, in the trigger. It cannot be a CHECK: an organization row
  is inserted before its first admin membership exists, so zero is a legal transient
  state at creation, and PostgreSQL does not support DEFERRABLE CHECK constraints.

Why a counter column rather than counting rows: a trigger that ran
``SELECT count(*) FROM memberships`` would be racy. Two concurrent transactions each
see a snapshot excluding the other's uncommitted row, both count one admin, both
insert, and the organization ends with three. The ``UPDATE organizations`` below takes
a row lock on the parent instead, so the second transaction blocks, re-reads the
committed value, and the CHECK fires.

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d569445357ca"
down_revision: str | Sequence[str] | None = "8839e1aa9553"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ADJUST_FN = """
CREATE OR REPLACE FUNCTION organizations_adjust_admin_count(
    p_organization_id uuid,
    p_delta integer
) RETURNS void AS $$
DECLARE
    v_count  integer;
    v_active boolean;
BEGIN
    -- Takes a row lock on the organization, which is what serializes concurrent
    -- membership writes for the same tenant. The ceiling CHECK fires here.
    UPDATE organizations
       SET active_admin_count = active_admin_count + p_delta
     WHERE id = p_organization_id
    RETURNING active_admin_count, is_active INTO v_count, v_active;

    -- No row means the organization is being deleted in this same statement and its
    -- memberships are cascading away. There is no counter left to maintain, and the
    -- floor must not fire on a tenant that is going away.
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- The floor. Only for organizations that are still active: deactivating a tenant
    -- and then clearing its members is legitimate.
    IF v_count = 0 AND v_active THEN
        RAISE EXCEPTION
            'organization % would be left with no active admin', p_organization_id
            USING ERRCODE = 'check_violation',
                  HINT = 'promote another member before removing or demoting the last admin';
    END IF;
END;
$$ LANGUAGE plpgsql;
"""

TRIGGER_FN = """
CREATE OR REPLACE FUNCTION memberships_maintain_admin_count() RETURNS trigger AS $$
DECLARE
    was_admin boolean := false;
    is_admin  boolean := false;
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.role = 'admin' AND NEW.status = 'active' THEN
            PERFORM organizations_adjust_admin_count(NEW.organization_id, 1);
        END IF;
        RETURN NEW;
    END IF;

    IF TG_OP = 'DELETE' THEN
        IF OLD.role = 'admin' AND OLD.status = 'active' THEN
            PERFORM organizations_adjust_admin_count(OLD.organization_id, -1);
        END IF;
        RETURN OLD;
    END IF;

    -- UPDATE. Both role and status can move a membership in or out of the count, so
    -- the test is the conjunction, not either column on its own.
    was_admin := (OLD.role = 'admin' AND OLD.status = 'active');
    is_admin  := (NEW.role = 'admin' AND NEW.status = 'active');

    IF OLD.organization_id IS DISTINCT FROM NEW.organization_id THEN
        -- Reparenting is two adjustments, and the old tenant's floor still applies.
        IF was_admin THEN
            PERFORM organizations_adjust_admin_count(OLD.organization_id, -1);
        END IF;
        IF is_admin THEN
            PERFORM organizations_adjust_admin_count(NEW.organization_id, 1);
        END IF;
    ELSIF was_admin AND NOT is_admin THEN
        PERFORM organizations_adjust_admin_count(NEW.organization_id, -1);
    ELSIF is_admin AND NOT was_admin THEN
        PERFORM organizations_adjust_admin_count(NEW.organization_id, 1);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# AFTER, so the row has already passed the memberships constraints, and FOR EACH ROW
# because a multi-row statement can move the count by more than one.
CREATE_TRIGGER = """
CREATE TRIGGER trg_memberships_maintain_admin_count
AFTER INSERT OR UPDATE OR DELETE ON memberships
FOR EACH ROW EXECUTE FUNCTION memberships_maintain_admin_count();
"""

# Reconcile any rows written before the trigger existed. A no-op on an empty database,
# and the difference between correct and silently wrong on one that is not.
BACKFILL = """
UPDATE organizations o
   SET active_admin_count = COALESCE(c.n, 0)
  FROM (
        SELECT id AS org_id,
               (SELECT count(*)
                  FROM memberships m
                 WHERE m.organization_id = organizations.id
                   AND m.role = 'admin'
                   AND m.status = 'active') AS n
          FROM organizations
       ) c
 WHERE o.id = c.org_id
   AND o.active_admin_count IS DISTINCT FROM COALESCE(c.n, 0);
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(ADJUST_FN)
    op.execute(TRIGGER_FN)
    op.execute(BACKFILL)
    op.execute(CREATE_TRIGGER)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_memberships_maintain_admin_count ON memberships;")
    op.execute("DROP FUNCTION IF EXISTS memberships_maintain_admin_count();")
    op.execute("DROP FUNCTION IF EXISTS organizations_adjust_admin_count(uuid, integer);")
