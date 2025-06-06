from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from accounts.models import Organization # Import Organization model
from rest_framework import serializers # Add this line
User = get_user_model()

class UserCreateSerializer(UserCreateSerializer):
    organization_type = serializers.SerializerMethodField() # Add this line

    class Meta(UserCreateSerializer.Meta):
        model = User
        # Add 'organization_type' to the fields tuple
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'password', 'is_active', 'organization_type')

    # Add this method to get the organization type
    def get_organization_type(self, obj):
        """
        Returns the organization type for the user's organization.
        """
        if obj.organization:
            return obj.organization.organization_type
        return None # Or return '' or a default value if the user has no organization
