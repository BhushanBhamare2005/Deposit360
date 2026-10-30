from enum import StrEnum


class Role(StrEnum):
    INSTITUTION_APPLICANT = "institution_applicant"
    INSTITUTION_USER = "institution_user"
    SCRUTINY_OFFICER = "scrutiny_officer"
    COMPLIANCE_ADMINISTRATOR = "compliance_administrator"
    FINANCE_OFFICER = "finance_officer"
    APPROVING_AUTHORITY = "approving_authority"
    ADMIN = "admin"
    AUDITOR = "auditor"


STAFF_ROLES = {
    Role.SCRUTINY_OFFICER,
    Role.COMPLIANCE_ADMINISTRATOR,
    Role.FINANCE_OFFICER,
    Role.APPROVING_AUTHORITY,
    Role.ADMIN,
    Role.AUDITOR,
}


def has_role(roles: list[str], *allowed: Role) -> bool:
    return bool(set(roles).intersection({role.value for role in allowed}))


def is_applicant(roles: list[str]) -> bool:
    return has_role(roles, Role.INSTITUTION_APPLICANT, Role.INSTITUTION_USER)


def is_staff(roles: list[str]) -> bool:
    return has_role(roles, *STAFF_ROLES)


def can_manage_compliance(roles: list[str]) -> bool:
    return has_role(roles, Role.COMPLIANCE_ADMINISTRATOR, Role.ADMIN)


def can_review_cases(roles: list[str]) -> bool:
    return can_manage_compliance(roles) or has_role(roles, Role.SCRUTINY_OFFICER)


def can_read_cases(roles: list[str]) -> bool:
    return can_review_cases(roles) or is_applicant(roles)


def can_review_finances(roles: list[str]) -> bool:
    return has_role(roles, Role.FINANCE_OFFICER, Role.ADMIN)


def can_approve_releases(roles: list[str]) -> bool:
    return has_role(roles, Role.APPROVING_AUTHORITY, Role.ADMIN)


def can_read_releases(roles: list[str]) -> bool:
    return is_applicant(roles) or can_review_finances(roles) or can_approve_releases(roles)


def can_review_verifications(roles: list[str]) -> bool:
    return can_manage_compliance(roles)


def can_view_audit(roles: list[str]) -> bool:
    return has_role(
        roles, Role.COMPLIANCE_ADMINISTRATOR, Role.APPROVING_AUTHORITY, Role.ADMIN, Role.AUDITOR
    )


def can_view_all_institutions(roles: list[str]) -> bool:
    return is_staff(roles)
