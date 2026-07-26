from rest_framework.permissions import SAFE_METHODS, BasePermission


class RolePermission(BasePermission):
    role = None

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == self.role)


class IsAdmin(RolePermission):
    role = "admin"


class IsSeller(RolePermission):
    role = "seller"


class IsInventoryManager(RolePermission):
    role = "inventory"


class IsDeliveryPartner(RolePermission):
    role = "delivery"


class IsSellerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in ("seller", "admin"))


class IsStaffRole(BasePermission):
    """Admin or inventory manager."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in ("admin", "inventory"))


class ReadOnlyOrSellerOwner(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.role in ("seller", "admin"))

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == "admin" or obj.seller_id == request.user.id
