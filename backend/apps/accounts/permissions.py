from rest_framework.permissions import BasePermission


class IsAppAdmin(BasePermission):
    """Checa o flag de negócio `User.is_admin` — não confundir com o `IsAdminUser` nativo do DRF,
    que checa `is_staff` (acesso ao Django Admin, coisa diferente)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)
