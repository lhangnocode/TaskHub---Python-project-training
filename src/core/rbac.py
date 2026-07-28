from enum import Enum


class ResourceRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


ROLE_HIERARCHY: dict[ResourceRole, int] = {
    ResourceRole.OWNER: 40,
    ResourceRole.ADMIN: 30,
    ResourceRole.EDITOR: 20,
    ResourceRole.VIEWER: 10,
}


def has_role_permission(
    user_role: ResourceRole | str, required_role: ResourceRole
) -> bool:
    try:
        current_role = (
            user_role
            if isinstance(user_role, ResourceRole)
            else ResourceRole(user_role)
        )
    except ValueError:
        return False

    return ROLE_HIERARCHY[current_role] >= ROLE_HIERARCHY[required_role]
