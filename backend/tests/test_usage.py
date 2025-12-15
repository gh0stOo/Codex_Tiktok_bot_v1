import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.services import usage  # type: ignore
from app import models  # type: ignore


def test_quota_enforced(db):
    org = models.Organization(name="TestOrg")
    db.add(org)
    db.commit()
    usage.log_usage(db, org.id, "video_generation")
    with pytest.raises(usage.QuotaExceeded):
        usage.enforce_quota(db, org.id, "video_generation", limit=1)


def test_tenant_isolation_membership(db):
    org1 = models.Organization(name="Org1")
    org2 = models.Organization(name="Org2")
    user1 = models.User(email="u1@test.com", hashed_password="hash")
    db.add_all([org1, org2, user1])
    db.commit()
    membership = models.Membership(user_id=user1.id, organization_id=org1.id)
    db.add(membership)
    db.commit()
    # user should only have membership in org1
    memberships = db.query(models.Membership).filter(models.Membership.user_id == user1.id).all()
    assert memberships[0].organization_id == org1.id
    assert all(m.organization_id != org2.id for m in memberships)
