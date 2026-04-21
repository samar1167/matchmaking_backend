from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.db.models import Case, Exists, F, IntegerField, OuterRef, Q, Sum, When
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import UserPlan, PaymentRecord, FeatureFlag, CompatibilityParameter
from .models import UserProfile, UserMatchPreference, UserMatch, UserConnection, PrivatePerson, CompatibilityScore, CompatibilityTransaction, AuthActionToken, ChatConversation, ChatMessage
from .serializers import (
    RegisterSerializer, UserProfileSerializer, UserMatchPreferenceSerializer, PrivatePersonSerializer,
    UserMatchSerializer, UserConnectionSerializer, UserConnectionRequestSerializer,
    CompatibilityScoreSerializer, CompatibilityRequestSerializer,
    ChatConversationSerializer, ChatMessageSerializer, ChatMessageCreateSerializer,
)
from .serializers import (PurchaseCreditsSerializer, PaymentRecordSerializer, CompatibilityParameterSerializer)
from .serializers import EmailTokenObtainPairSerializer
from .serializers import VerifyEmailSerializer, EmailAddressSerializer, ResetPasswordSerializer
from .astrology_service import AstrologyService
import logging
logger = logging.getLogger(__name__)
User = get_user_model()


def chat_user_group_name(user_id):
    return f'chat_user_{user_id}'


def publish_chat_event(user_ids, payload):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
    except ImportError:
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    for user_id in set(user_ids):
        try:
            async_to_sync(channel_layer.group_send)(
                chat_user_group_name(user_id),
                {
                    'type': 'chat.message',
                    'payload': payload,
                },
            )
        except Exception as exc:
            logger.warning("Failed to publish chat event for user %s: %s", user_id, exc)


def get_or_create_chat_conversation(connection):
    low_id, high_id = sorted((connection.requester_id, connection.receiver_id))
    return ChatConversation.objects.get_or_create(
        connection=connection,
        defaults={
            'user_a_id': low_id,
            'user_b_id': high_id,
        },
    )


def send_auth_action_email(user, token_record):
    base_url = settings.FRONTEND_BASE_URL.rstrip('/')
    if token_record.purpose == AuthActionToken.PURPOSE_EMAIL_VERIFICATION:
        path = settings.EMAIL_VERIFICATION_PATH
        subject = 'Verify your Matchmaking account'
        action_text = 'verify your email address'
    else:
        path = settings.PASSWORD_RESET_PATH
        subject = 'Reset your Matchmaking password'
        action_text = 'reset your password'

    action_url = f"{base_url}{path}?token={token_record.token}"
    message = (
        f"Hello,\n\n"
        f"Use the link below to {action_text}:\n"
        f"{action_url}\n\n"
        f"This link expires at {token_record.expires_at.isoformat()}.\n"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def issue_and_send_token(user, purpose):
    if purpose == AuthActionToken.PURPOSE_EMAIL_VERIFICATION:
        lifetime = settings.EMAIL_VERIFICATION_TOKEN_LIFETIME
    else:
        lifetime = settings.PASSWORD_RESET_TOKEN_LIFETIME
    token_record = AuthActionToken.issue_token(user=user, purpose=purpose, lifetime=lifetime)
    send_auth_action_email(user, token_record)
    return token_record

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        issue_and_send_token(user, AuthActionToken.PURPOSE_EMAIL_VERIFICATION)


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response({'error': 'Both old_password and new_password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            return Response({'error': 'Old password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response({'error': list(e)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)


class VerifyEmailView(generics.GenericAPIView):
    serializer_class = VerifyEmailSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.validated_data['record']
        user = record.user
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
        record.mark_used()
        return Response({'detail': 'Email verified successfully.'}, status=status.HTTP_200_OK)


class ResendVerificationView(generics.GenericAPIView):
    serializer_class = EmailAddressSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(email__iexact=email).first()
        if user and not user.is_active:
            issue_and_send_token(user, AuthActionToken.PURPOSE_EMAIL_VERIFICATION)
        return Response(
            {'detail': 'If the account exists and is unverified, a verification email has been sent.'},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = EmailAddressSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            issue_and_send_token(user, AuthActionToken.PURPOSE_PASSWORD_RESET)
        return Response(
            {'detail': 'If the account exists, a password reset email has been sent.'},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.validated_data['record']
        user = record.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        record.mark_used()
        AuthActionToken.objects.filter(
            user=user,
            purpose=AuthActionToken.PURPOSE_PASSWORD_RESET,
            used_at__isnull=True,
        ).exclude(pk=record.pk).delete()
        return Response({'detail': 'Password reset successfully.'}, status=status.HTTP_200_OK)

class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    @action(detail=False, methods=['get', 'post', 'put', 'patch'])
    def me(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            profile = None
        if request.method == 'GET':
            if not profile:
                return Response({'detail': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(UserProfileSerializer(profile).data)
        serializer = UserProfileSerializer(profile, data=request.data, partial=request.method in ('PUT', 'PATCH'))
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK if profile else status.HTTP_201_CREATED)

class PrivatePersonViewSet(viewsets.ModelViewSet):
    serializer_class = PrivatePersonSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return PrivatePerson.objects.filter(owner=self.request.user)
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class UserMatchPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = UserMatchPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserMatchPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get', 'post', 'put', 'patch'])
    def me(self, request):
        try:
            preferences = UserMatchPreference.objects.get(user=request.user)
        except UserMatchPreference.DoesNotExist:
            preferences = None

        if request.method == 'GET':
            if not preferences:
                return Response({'detail': 'Match preferences not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(UserMatchPreferenceSerializer(preferences).data)

        serializer = UserMatchPreferenceSerializer(
            preferences,
            data=request.data,
            partial=request.method in ('PUT', 'PATCH'),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK if preferences else status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def matches(self, request):
        preferences = get_object_or_404(UserMatchPreference, user=request.user)
        try:
            limit = min(int(request.query_params.get('limit', 20)), 100)
        except ValueError:
            return Response({'error': 'limit must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        if limit < 1:
            return Response({'error': 'limit must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

        candidates = preferences.apply_to_profiles(
            UserProfile.objects.select_related('user', 'user__match_preferences')
        )[:limit]
        return Response(UserProfileSerializer(candidates, many=True).data)


class UserMatchViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        existing_connections = UserConnection.objects.filter(
            Q(requester=profile, receiver=OuterRef('matched_user')) |
            Q(requester=OuterRef('matched_user'), receiver=profile)
        )
        matches = (
            UserMatch.objects
            .filter(user=profile)
            .annotate(has_existing_connection=Exists(existing_connections))
            .filter(has_existing_connection=False)
            .select_related('matched_user__user')
            .order_by('?')[:3]
        )
        return Response(UserMatchSerializer(matches, many=True).data)


class UserConnectionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _current_profile(self, request):
        return get_object_or_404(UserProfile, user=request.user)

    def _base_queryset(self, profile):
        return (
            UserConnection.objects
            .filter(Q(requester=profile) | Q(receiver=profile))
            .select_related('requester__user', 'receiver__user')
            .order_by('-updated_at')
        )

    def _serialize(self, connection, request, status_code=status.HTTP_200_OK):
        serializer = UserConnectionSerializer(connection, context={'request': request})
        return Response(serializer.data, status=status_code)

    def list(self, request):
        profile = self._current_profile(request)
        queryset = self._base_queryset(profile)

        connection_status = request.query_params.get('status')
        if connection_status:
            valid_statuses = {choice[0] for choice in UserConnection.STATUS_CHOICES}
            if connection_status not in valid_statuses:
                return Response({'error': 'Invalid connection status.'}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(status=connection_status)

        role = request.query_params.get('role')
        if role == 'sent':
            queryset = queryset.filter(requester=profile)
        elif role == 'received':
            queryset = queryset.filter(receiver=profile)
        elif role:
            return Response({'error': 'role must be sent or received.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(UserConnectionSerializer(queryset, many=True, context={'request': request}).data)

    @action(detail=False, methods=['post'])
    def request(self, request):
        serializer = UserConnectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        requester = self._current_profile(request)
        receiver = get_object_or_404(UserProfile, id=serializer.validated_data['matched_user_profile_id'])

        if requester.id == receiver.id:
            return Response({'error': 'Cannot connect with yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        if not UserMatch.objects.filter(user=requester, matched_user=receiver).exists():
            return Response({'error': 'Connections can only be requested for matched users.'}, status=status.HTTP_400_BAD_REQUEST)

        low_id, high_id = sorted((requester.id, receiver.id))
        try:
            with db_transaction.atomic():
                existing = (
                    UserConnection.objects
                    .select_for_update()
                    .filter(profile_low_id=low_id, profile_high_id=high_id)
                    .select_related('requester__user', 'receiver__user')
                    .first()
                )
                if existing:
                    return self._serialize(existing, request)

                connection = UserConnection.objects.create(
                    requester=requester,
                    receiver=receiver,
                    profile_low_id=low_id,
                    profile_high_id=high_id,
                    status=UserConnection.STATUS_PENDING,
                )
        except IntegrityError:
            connection = get_object_or_404(
                UserConnection.objects.select_related('requester__user', 'receiver__user'),
                profile_low_id=low_id,
                profile_high_id=high_id,
            )
            return self._serialize(connection, request)

        return self._serialize(connection, request, status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        profile = self._current_profile(request)
        connection = get_object_or_404(self._base_queryset(profile), pk=pk)

        if connection.receiver_id != profile.id:
            return Response({'error': 'Only the receiver can accept this connection.'}, status=status.HTTP_403_FORBIDDEN)
        if connection.status != UserConnection.STATUS_PENDING:
            return Response({'error': 'Only pending connections can be accepted.'}, status=status.HTTP_400_BAD_REQUEST)

        connection.status = UserConnection.STATUS_ACCEPTED
        connection.responded_at = timezone.now()
        connection.save(update_fields=['status', 'responded_at', 'updated_at'])
        get_or_create_chat_conversation(connection)
        return self._serialize(connection, request)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        profile = self._current_profile(request)
        connection = get_object_or_404(self._base_queryset(profile), pk=pk)

        if connection.receiver_id != profile.id:
            return Response({'error': 'Only the receiver can decline this connection.'}, status=status.HTTP_403_FORBIDDEN)
        if connection.status != UserConnection.STATUS_PENDING:
            return Response({'error': 'Only pending connections can be declined.'}, status=status.HTTP_400_BAD_REQUEST)

        connection.status = UserConnection.STATUS_DECLINED
        connection.responded_at = timezone.now()
        connection.save(update_fields=['status', 'responded_at', 'updated_at'])
        return self._serialize(connection, request)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        profile = self._current_profile(request)
        connection = get_object_or_404(self._base_queryset(profile), pk=pk)

        if connection.requester_id != profile.id:
            return Response({'error': 'Only the requester can cancel this connection.'}, status=status.HTTP_403_FORBIDDEN)
        if connection.status != UserConnection.STATUS_PENDING:
            return Response({'error': 'Only pending connections can be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        connection.status = UserConnection.STATUS_CANCELLED
        connection.responded_at = timezone.now()
        connection.save(update_fields=['status', 'responded_at', 'updated_at'])
        return self._serialize(connection, request)

    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        profile = self._current_profile(request)
        connection = get_object_or_404(self._base_queryset(profile), pk=pk)

        if connection.status != UserConnection.STATUS_ACCEPTED:
            return Response({'error': 'Only accepted connections can be disconnected.'}, status=status.HTTP_400_BAD_REQUEST)

        connection.status = UserConnection.STATUS_DISCONNECTED
        connection.save(update_fields=['status', 'updated_at'])
        return self._serialize(connection, request)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        profile = self._current_profile(request)
        queryset = self._base_queryset(profile).filter(status=UserConnection.STATUS_PENDING)
        return Response(UserConnectionSerializer(queryset, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def received(self, request):
        profile = self._current_profile(request)
        queryset = self._base_queryset(profile).filter(receiver=profile, status=UserConnection.STATUS_PENDING)
        return Response(UserConnectionSerializer(queryset, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def sent(self, request):
        profile = self._current_profile(request)
        queryset = self._base_queryset(profile).filter(requester=profile, status=UserConnection.STATUS_PENDING)
        return Response(UserConnectionSerializer(queryset, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def accepted(self, request):
        profile = self._current_profile(request)
        queryset = self._base_queryset(profile).filter(status=UserConnection.STATUS_ACCEPTED)
        return Response(UserConnectionSerializer(queryset, many=True, context={'request': request}).data)


class ChatConversationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _current_profile(self, request):
        return get_object_or_404(UserProfile, user=request.user)

    def _base_queryset(self, profile):
        return (
            ChatConversation.objects
            .filter(Q(user_a=profile) | Q(user_b=profile))
            .select_related(
                'connection',
                'user_a__user',
                'user_b__user',
                'last_message__sender__user',
                'last_message__receiver__user',
            )
        )

    def _serialize(self, conversation, request, status_code=status.HTTP_200_OK):
        serializer = ChatConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status_code)

    def _conversation_for_request(self, request, pk):
        profile = self._current_profile(request)
        conversation = get_object_or_404(self._base_queryset(profile), pk=pk)
        return profile, conversation

    def list(self, request):
        profile = self._current_profile(request)
        queryset = self._base_queryset(profile).order_by('-last_message_at', '-updated_at', '-id')
        return Response(ChatConversationSerializer(queryset, many=True, context={'request': request}).data)

    def retrieve(self, request, pk=None):
        _, conversation = self._conversation_for_request(request, pk)
        return self._serialize(conversation, request)

    @action(detail=False, methods=['post'], url_path=r'from-connection/(?P<connection_id>[^/.]+)')
    def from_connection(self, request, connection_id=None):
        profile = self._current_profile(request)
        connection = get_object_or_404(
            UserConnection.objects.select_related('requester__user', 'receiver__user'),
            pk=connection_id,
        )

        if profile.id not in (connection.requester_id, connection.receiver_id):
            return Response({'error': 'You are not part of this connection.'}, status=status.HTTP_403_FORBIDDEN)
        if connection.status != UserConnection.STATUS_ACCEPTED:
            return Response({'error': 'Chat is only available for accepted connections.'}, status=status.HTTP_400_BAD_REQUEST)

        conversation, created = get_or_create_chat_conversation(connection)
        conversation = self._base_queryset(profile).get(pk=conversation.pk)
        return self._serialize(conversation, request, status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        profile, conversation = self._conversation_for_request(request, pk)

        if request.method == 'GET':
            try:
                limit = min(int(request.query_params.get('limit', 50)), 100)
            except ValueError:
                return Response({'error': 'limit must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
            if limit < 1:
                return Response({'error': 'limit must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

            messages = (
                ChatMessage.objects
                .filter(conversation=conversation, deleted_at__isnull=True)
                .select_related('sender__user', 'receiver__user')
                .order_by('-id')
            )
            before = request.query_params.get('before')
            if before:
                try:
                    messages = messages.filter(id__lt=int(before))
                except ValueError:
                    return Response({'error': 'before must be a message id.'}, status=status.HTTP_400_BAD_REQUEST)

            page = list(messages[:limit + 1])
            has_more = len(page) > limit
            page = page[:limit]
            next_before = page[-1].id if has_more and page else None
            return Response({
                'results': ChatMessageSerializer(page, many=True).data,
                'next_before': next_before,
            })

        serializer = ChatMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        body = serializer.validated_data['body']
        client_message_id = serializer.validated_data.get('client_message_id')
        notify_base_payload = None
        sender_unread_count = 0
        receiver_unread_count = 0

        with db_transaction.atomic():
            locked = (
                ChatConversation.objects
                .select_for_update()
                .select_related('connection', 'user_a__user', 'user_b__user')
                .get(pk=conversation.pk)
            )
            if locked.connection.status != UserConnection.STATUS_ACCEPTED:
                return Response({'error': 'Chat is only available for accepted connections.'}, status=status.HTTP_400_BAD_REQUEST)

            receiver = locked.other_profile(profile)
            if receiver is None:
                return Response({'error': 'You are not part of this conversation.'}, status=status.HTTP_403_FORBIDDEN)

            if client_message_id:
                existing = ChatMessage.objects.filter(sender=profile, client_message_id=client_message_id).first()
                if existing:
                    return Response(ChatMessageSerializer(existing).data, status=status.HTTP_200_OK)

            message = ChatMessage.objects.create(
                conversation=locked,
                sender=profile,
                receiver=receiver,
                body=body,
                client_message_id=client_message_id,
            )

            update_fields = {
                'last_message': message,
                'last_message_at': message.created_at,
            }
            if receiver.id == locked.user_a_id:
                update_fields['user_a_unread_count'] = F('user_a_unread_count') + 1
                update_fields['user_b_last_read_message'] = message
            else:
                update_fields['user_b_unread_count'] = F('user_b_unread_count') + 1
                update_fields['user_a_last_read_message'] = message

            ChatConversation.objects.filter(pk=locked.pk).update(**update_fields)
            locked.refresh_from_db()
            message = ChatMessage.objects.select_related('sender__user', 'receiver__user').get(pk=message.pk)

            message_payload = ChatMessageSerializer(message).data
            sender_unread_count = locked.unread_count_for(profile)
            receiver_unread_count = locked.unread_count_for(receiver)
            notify_base_payload = {
                'type': 'message.created',
                'conversationId': locked.id,
                'message': message_payload,
            }

        publish_chat_event([receiver.user_id], {
            **notify_base_payload,
            'unreadCount': receiver_unread_count,
            'totalUnreadCount': total_unread_count_for_profile(receiver),
        })
        publish_chat_event([profile.user_id], {
            **notify_base_payload,
            'unreadCount': sender_unread_count,
            'totalUnreadCount': total_unread_count_for_profile(profile),
        })
        return Response(ChatMessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        profile, conversation = self._conversation_for_request(request, pk)

        with db_transaction.atomic():
            locked = ChatConversation.objects.select_for_update().get(pk=conversation.pk)
            latest_message_id = locked.last_message_id
            if profile.id == locked.user_a_id:
                locked.user_a_unread_count = 0
                locked.user_a_last_read_message_id = latest_message_id
                update_fields = ['user_a_unread_count', 'user_a_last_read_message', 'updated_at']
            else:
                locked.user_b_unread_count = 0
                locked.user_b_last_read_message_id = latest_message_id
                update_fields = ['user_b_unread_count', 'user_b_last_read_message', 'updated_at']
            locked.save(update_fields=update_fields)

        total_unread = total_unread_count_for_profile(profile)
        payload = {
            'type': 'conversation.read',
            'conversationId': locked.id,
            'unreadCount': 0,
            'totalUnreadCount': total_unread,
        }
        publish_chat_event([profile.user_id], payload)
        return Response(payload)


def total_unread_count_for_profile(profile):
    total = ChatConversation.objects.filter(Q(user_a=profile) | Q(user_b=profile)).aggregate(
        total=Sum(
            Case(
                When(user_a=profile, then=F('user_a_unread_count')),
                When(user_b=profile, then=F('user_b_unread_count')),
                default=0,
                output_field=IntegerField(),
            )
        )
    )['total']
    return total or 0


class ChatUnreadCountView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        return Response({'totalUnreadCount': total_unread_count_for_profile(profile)})


class CompatibilityViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def check(self, request):
        req_ser = CompatibilityRequestSerializer(data=request.data)
        req_ser.is_valid(raise_exception=True)
        data = req_ser.validated_data

        try:
            user_profile = get_object_or_404(UserProfile, user=request.user)

            # ── Credit check ──
            plan, _ = UserPlan.objects.get_or_create(user=request.user)
            if plan.total_credits == 0:
                return Response({
                    'error': 'No credits remaining. Please purchase credits to continue.',
                    'credits_remaining': 0,
                    'purchase_url': '/api/plan/purchase/',
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

            # ── Resolve target ──
            if data.get('matched_user_id'):
                target = get_object_or_404(UserProfile, id=data['matched_user_id'])
                filter_kwargs = {'user': user_profile, 'matched_user': target, 'matched_private_person': None}
            else:
                target = get_object_or_404(PrivatePerson, id=data['matched_private_person_id'], owner=request.user)
                filter_kwargs = {'user': user_profile, 'matched_user': None, 'matched_private_person': target}

            # ── Call astrology API ──
            compat_data = AstrologyService.get_compatibility(
                user_profile, target,
            )

            with db_transaction.atomic():
                # ── Consume one credit (paid first, then free) ──
                credit_type = plan.consume_credit()
                is_paid_session = (credit_type == 'paid')

                # ── Persist latest result ──
                defaults = {
                    'is_paid':             is_paid_session,
                    'overall_score':       compat_data['compatibility_score'],
                    'sun_compatibility':   compat_data.get('sun_compatibility'),
                    'moon_compatibility':  compat_data.get('moon_compatibility'),
                    'venus_compatibility': compat_data.get('venus_compatibility'),
                    'mars_compatibility':  compat_data.get('mars_compatibility'),
                    'description':         compat_data.get('description', ''),
                    'api_response':        compat_data.get('api_response'),
                }
                obj, _ = CompatibilityScore.objects.update_or_create(**filter_kwargs, defaults=defaults)

                # ── Append successful compatibility API transaction ──
                CompatibilityTransaction.objects.create(
                    **filter_kwargs,
                    compatibility_score=obj,
                    credit_type=credit_type,
                    is_paid=is_paid_session,
                    overall_score=compat_data['compatibility_score'],
                    credits_remaining_after=plan.total_credits,
                    description=compat_data.get('description', ''),
                    api_response=compat_data.get('api_response'),
                )

            # ── Serialize with plan context ──
            serializer = CompatibilityScoreSerializer(obj, context={'request': request})
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Compatibility check error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def history(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        qs = CompatibilityScore.objects.filter(user=profile).order_by('-created_at')
        return Response(CompatibilityScoreSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def top_matches(self, request):
        limit   = int(request.query_params.get('limit', 10))
        profile = get_object_or_404(UserProfile, user=request.user)
        qs      = CompatibilityScore.objects.filter(user=profile).order_by('-overall_score')[:limit]
        return Response(CompatibilityScoreSerializer(qs, many=True, context={'request': request}).data)
    

class PlanViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's credit balance."""
        plan, _ = UserPlan.objects.get_or_create(user=request.user)
        config   = FeatureFlag.get()
        return Response({
            'free_credits':         plan.free_credits,
            'paid_credits':         plan.paid_credits,
            'total_credits':        plan.total_credits,
            'paid_credit_price_usd': str(config.paid_credit_price_usd),
            'credits_per_purchase': config.credits_per_purchase,
        })

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        """
        Record a credit purchase after payment is confirmed.
        In production: verify the payment_reference with your
        payment gateway (Stripe, Razorpay, etc.) before adding credits.
        """
        serializer = PurchaseCreditsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        config = FeatureFlag.get()
        plan, _ = UserPlan.objects.get_or_create(user=request.user)

        # Record the payment
        payment = PaymentRecord.objects.create(
            user=request.user,
            amount_usd=config.paid_credit_price_usd * config.credits_per_purchase,
            credits_purchased=config.credits_per_purchase,
            status='completed',
            payment_reference=serializer.validated_data['payment_reference'],
            completed_at=timezone.now(),
        )

        # Add credits to wallet
        plan.add_paid_credits(config.credits_per_purchase)

        return Response({
            'detail': f'{config.credits_per_purchase} paid credits added to your account.',
            'credits_purchased': config.credits_per_purchase,
            'paid_credits':      plan.paid_credits,
            'total_credits':     plan.total_credits,
            'payment_id':        payment.id,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def payment_history(self, request):
        """List all payments made by current user."""
        payments = PaymentRecord.objects.filter(user=request.user)
        return Response(PaymentRecordSerializer(payments, many=True).data)

    @action(detail=False, methods=['get'])
    def parameters(self, request):
        """
        List all compatibility parameters with free/paid status.
        Useful for the frontend to show what's locked vs unlocked.
        """
        params = CompatibilityParameter.objects.filter(is_active=True)
        return Response(CompatibilityParameterSerializer(params, many=True).data)
