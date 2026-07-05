from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer
from django.contrib.auth import authenticate
from .models import Transaction
import random


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    full_name = serializers.CharField(write_only=True)
    mobile = serializers.CharField(write_only=True)
    date_of_birth = serializers.DateField(write_only=True)
    address = serializers.CharField(write_only=True)
    account_type = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "full_name",
            "mobile",
            "date_of_birth",
            "address",
            "account_type",
        ]

    def create(self, validated_data):

        full_name = validated_data.pop("full_name")
        mobile = validated_data.pop("mobile")
        dob = validated_data.pop("date_of_birth")
        address = validated_data.pop("address")
        account_type = validated_data.pop("account_type")

        user = User.objects.create_user(**validated_data)

        account_number = "SBP" + str(random.randint(10000000, 99999999))

        Customer.objects.create(
            user=user,
            full_name=full_name,
            email=user.email,
            mobile=mobile,
            date_of_birth=dob,
            address=address,
            account_type=account_type,
            account_number=account_number,
        )

        return user
class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):

        user = authenticate(
            username=data["username"],
            password=data["password"]
        )

        if user is None:
            raise serializers.ValidationError(
                "Invalid username or password."
            )

        data["user"] = user
        return data
class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transaction
        fields = [
            "transaction_type",
            "amount",
            "balance_after",
            "receiver_account",
            "remarks",
            "status",
            "created_at",
        ]