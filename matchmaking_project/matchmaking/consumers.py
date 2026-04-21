from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .views import chat_user_group_name


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.group_name = chat_user_group_name(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Message writes stay on the HTTP API so retries and validation remain simple.
        return

    async def chat_message(self, event):
        await self.send_json(event['payload'])
