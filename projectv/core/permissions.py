"""
Custom permission classes for the core app
"""

from rest_framework import permissions
from .models import Company


class IsCompanyOwner(permissions.BasePermission):
    """
    Permission class to ensure user can only access their own company's data
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and has a company"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # For list/create views, just check if user has at least one company
        if view.action in ['list', 'create']:
            return request.user.companies.exists()
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check if user owns the company associated with the object"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # If object is a Company, check direct ownership
        if isinstance(obj, Company):
            return obj.owner == request.user
        
        # If object has a company field, check ownership through company
        if hasattr(obj, 'company'):
            return obj.company.owner == request.user
        
        # If object is related to a company through other relationships
        if hasattr(obj, 'account') and hasattr(obj.account, 'company'):
            return obj.account.company.owner == request.user
        
        if hasattr(obj, 'connection') and hasattr(obj.connection, 'company'):
            return obj.connection.company.owner == request.user
        
        # Default to checking if user owns any companies
        return request.user.companies.exists()


class IsCompanyMember(permissions.BasePermission):
    """
    Permission class for company members (not just owners)
    Can be extended later for multi-user companies
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and associated with a company"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # For now, same as IsCompanyOwner
        return request.user.companies.exists()
    
    def has_object_permission(self, request, view, obj):
        """Check if user has access to the company's data"""
        # For now, same as IsCompanyOwner
        # TODO: Extend for multiple users per company
        return IsCompanyOwner().has_object_permission(request, view, obj)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners to edit objects.
    Others get read-only access.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only to the owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        if hasattr(obj, 'company'):
            return obj.company.owner == request.user
        
        return False
