from flask_login import UserMixin
from datetime import datetime
import json
import os
import redis

# Initialize Redis client
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=0
)

class User(UserMixin):
    """User model for LinkedIn authentication"""
    
    def __init__(self, id, linkedin_id, name, email, profile_pic=None, access_token=None):
        self.id = id
        self.linkedin_id = linkedin_id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic
        self.access_token = access_token
        self.conversations = []
    
    def save(self):
        """Save user to Redis"""
        user_data = {
            'id': self.id,
            'linkedin_id': self.linkedin_id,
            'name': self.name,
            'email': self.email,
            'profile_pic': self.profile_pic,
            'access_token': self.access_token,
            'conversations': self.conversations
        }
        redis_client.set(f'user:{self.id}', json.dumps(user_data))
        return self
    
    @staticmethod
    def get(user_id):
        """Retrieve user from Redis"""
        user_data = redis_client.get(f'user:{user_id}')
        if user_data:
            user_dict = json.loads(user_data)
            user = User(
                id=user_dict['id'],
                linkedin_id=user_dict['linkedin_id'],
                name=user_dict['name'],
                email=user_dict['email'],
                profile_pic=user_dict.get('profile_pic'),
                access_token=user_dict.get('access_token')
            )
            user.conversations = user_dict.get('conversations', [])
            return user
        return None
    
    @staticmethod
    def get_by_linkedin_id(linkedin_id):
        """Find user by LinkedIn ID"""
        user_ids = redis_client.keys('user:*')
        for user_id in user_ids:
            user_data = redis_client.get(user_id)
            if user_data:
                user_dict = json.loads(user_data)
                if user_dict.get('linkedin_id') == linkedin_id:
                    return User.get(user_dict['id'])
        return None


class Message:
    """Message model for conversations"""
    
    def __init__(self, id, conversation_id, sender_id, content, timestamp=None, is_read=False):
        self.id = id
        self.conversation_id = conversation_id
        self.sender_id = sender_id
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.is_read = is_read
    
    def to_dict(self):
        """Convert message to dictionary"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'timestamp': self.timestamp,
            'is_read': self.is_read
        }
    
    @staticmethod
    def from_dict(data):
        """Create message from dictionary"""
        return Message(
            id=data['id'],
            conversation_id=data['conversation_id'],
            sender_id=data['sender_id'],
            content=data['content'],
            timestamp=data['timestamp'],
            is_read=data['is_read']
        )
    
    def save(self):
        """Save message to Redis"""
        redis_client.lpush(
            f'conversation:{self.conversation_id}:messages',
            json.dumps(self.to_dict())
        )
        return self
    
    @staticmethod
    def get_messages(conversation_id, limit=50, offset=0):
        """Get messages for a conversation"""
        messages_data = redis_client.lrange(
            f'conversation:{conversation_id}:messages',
            offset,
            offset + limit - 1
        )
        
        messages = []
        for msg_data in messages_data:
            msg_dict = json.loads(msg_data)
            messages.append(Message.from_dict(msg_dict))
        
        return messages


class Conversation:
    """Conversation model for user interactions"""
    
    def __init__(self, id, participants, title=None, last_message=None, created_at=None):
        self.id = id
        self.participants = participants  # List of user IDs
        self.title = title
        self.last_message = last_message
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self):
        """Convert conversation to dictionary"""
        return {
            'id': self.id,
            'participants': self.participants,
            'title': self.title,
            'last_message': self.last_message,
            'created_at': self.created_at
        }
    
    @staticmethod
    def from_dict(data):
        """Create conversation from dictionary"""
        return Conversation(
            id=data['id'],
            participants=data['participants'],
            title=data.get('title'),
            last_message=data.get('last_message'),
            created_at=data.get('created_at')
        )
    
    def save(self):
        """Save conversation to Redis"""
        redis_client.set(
            f'conversation:{self.id}',
            json.dumps(self.to_dict())
        )
        
        # Update user conversation lists
        for user_id in self.participants:
            user = User.get(user_id)
            if user and self.id not in user.conversations:
                user.conversations.append(self.id)
                user.save()
        
        return self
    
    @staticmethod
    def get(conversation_id):
        """Get conversation by ID"""
        conv_data = redis_client.get(f'conversation:{conversation_id}')
        if conv_data:
            return Conversation.from_dict(json.loads(conv_data))
        return None
    
    @staticmethod
    def get_for_user(user_id):
        """Get all conversations for a user"""
        user = User.get(user_id)
        if not user:
            return []
        
        conversations = []
        for conv_id in user.conversations:
            conv = Conversation.get(conv_id)
            if conv:
                conversations.append(conv)
        
        # Sort by last message timestamp (most recent first)
        return sorted(
            conversations,
            key=lambda c: c.last_message.get('timestamp', c.created_at) if c.last_message else c.created_at,
            reverse=True
        )
