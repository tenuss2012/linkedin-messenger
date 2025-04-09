from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from requests_oauthlib import OAuth2Session
import uuid
import requests
import json
import os
from app.models import User, Conversation, Message
from app import socketio

# Create blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# LinkedIn OAuth configuration
LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET')
LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI')
LINKEDIN_AUTHORIZATION_URL = 'https://www.linkedin.com/oauth/v2/authorization'
LINKEDIN_TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'
LINKEDIN_API_BASE_URL = 'https://api.linkedin.com/v2'

# Main routes
@main_bp.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.conversations'))
    return render_template('index.html')

@main_bp.route('/conversations')
@login_required
def conversations():
    """Show all conversations for the current user"""
    user_conversations = Conversation.get_for_user(current_user.id)
    return render_template('conversations.html', conversations=user_conversations)

@main_bp.route('/conversation/<conversation_id>')
@login_required
def conversation_detail(conversation_id):
    """Show a specific conversation with messages"""
    conversation = Conversation.get(conversation_id)
    if not conversation or current_user.id not in conversation.participants:
        flash('Conversation not found or access denied.', 'error')
        return redirect(url_for('main.conversations'))
    
    messages = Message.get_messages(conversation_id)
    participants = [User.get(user_id) for user_id in conversation.participants]
    
    return render_template(
        'conversation_detail.html',
        conversation=conversation,
        messages=messages,
        participants=participants
    )

@main_bp.route('/api/conversations')
@login_required
def api_conversations():
    """API endpoint to get user conversations"""
    user_conversations = Conversation.get_for_user(current_user.id)
    
    # Convert to list of dicts for JSON serialization
    result = []
    for conv in user_conversations:
        conv_dict = conv.to_dict()
        # Add participant names for display
        conv_dict['participant_details'] = []
        for user_id in conv.participants:
            if user_id != current_user.id:  # Skip current user
                user = User.get(user_id)
                if user:
                    conv_dict['participant_details'].append({
                        'id': user.id,
                        'name': user.name,
                        'profile_pic': user.profile_pic
                    })
        result.append(conv_dict)
    
    return jsonify(result)

@main_bp.route('/api/messages/<conversation_id>')
@login_required
def api_messages(conversation_id):
    """API endpoint to get messages for a conversation"""
    conversation = Conversation.get(conversation_id)
    if not conversation or current_user.id not in conversation.participants:
        return jsonify({'error': 'Conversation not found or access denied'}), 403
    
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    messages = Message.get_messages(conversation_id, limit, offset)
    
    # Convert to list of dicts for JSON serialization
    result = [msg.to_dict() for msg in messages]
    
    return jsonify(result)

@main_bp.route('/api/send-message', methods=['POST'])
@login_required
def api_send_message():
    """API endpoint to send a message"""
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('conversation_id') or not data.get('content'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conversation_id = data['conversation_id']
    content = data['content']
    
    # Verify user is part of the conversation
    conversation = Conversation.get(conversation_id)
    if not conversation or current_user.id not in conversation.participants:
        return jsonify({'error': 'Conversation not found or access denied'}), 403
    
    # Create and save the message
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=content
    ).save()
    
    # Update conversation's last message
    conversation.last_message = {
        'content': content,
        'sender_id': current_user.id,
        'timestamp': message.timestamp
    }
    conversation.save()
    
    # Emit the message via Socket.IO to all participants
    message_data = message.to_dict()
    message_data['sender_name'] = current_user.name
    message_data['sender_pic'] = current_user.profile_pic
    
    for participant_id in conversation.participants:
        if participant_id != current_user.id:  # Don't send to the sender
            socketio.emit(
                'new_message',
                message_data,
                room=f'user_{participant_id}'
            )
    
    return jsonify(message_data)

# Auth routes
@auth_bp.route('/login')
def login():
    """Redirect to LinkedIn OAuth flow"""
    linkedin = OAuth2Session(
        LINKEDIN_CLIENT_ID,
        redirect_uri=LINKEDIN_REDIRECT_URI,
        scope=['r_liteprofile', 'r_emailaddress']
    )
    authorization_url, state = linkedin.authorization_url(LINKEDIN_AUTHORIZATION_URL)
    
    # Save state for OAuth verification
    session['oauth_state'] = state
    
    return redirect(authorization_url)

@auth_bp.route('/callback')
def callback():
    """Handle LinkedIn OAuth callback"""
    if 'error' in request.args:
        flash(f"Error during authentication: {request.args.get('error_description', 'Unknown error')}", 'error')
        return redirect(url_for('main.index'))
    
    # Verify OAuth state
    if request.args.get('state') != session.get('oauth_state'):
        flash('OAuth state mismatch. Please try again.', 'error')
        return redirect(url_for('main.index'))
    
    # Exchange code for token
    linkedin = OAuth2Session(
        LINKEDIN_CLIENT_ID,
        redirect_uri=LINKEDIN_REDIRECT_URI
    )
    
    token = linkedin.fetch_token(
        LINKEDIN_TOKEN_URL,
        client_secret=LINKEDIN_CLIENT_SECRET,
        authorization_response=request.url
    )
    
    # Get LinkedIn profile data
    headers = {'Authorization': f"Bearer {token['access_token']}"}
    
    # Get basic profile
    profile_resp = requests.get(
        f"{LINKEDIN_API_BASE_URL}/me",
        headers=headers
    )
    profile_data = profile_resp.json()
    
    # Get email address
    email_resp = requests.get(
        f"{LINKEDIN_API_BASE_URL}/emailAddress?q=members&projection=(elements*(handle~))",
        headers=headers
    )
    email_data = email_resp.json()
    
    # Extract user information
    linkedin_id = profile_data.get('id')
    if not linkedin_id:
        flash('Failed to retrieve profile information from LinkedIn.', 'error')
        return redirect(url_for('main.index'))
    
    # Get name from profile
    first_name = profile_data.get('localizedFirstName', '')
    last_name = profile_data.get('localizedLastName', '')
    name = f"{first_name} {last_name}".strip()
    
    # Get email from email response
    email = None
    try:
        email = email_data['elements'][0]['handle~']['emailAddress']
    except (KeyError, IndexError):
        # Email might not be available
        pass
    
    # Check if user already exists
    user = User.get_by_linkedin_id(linkedin_id)
    
    if not user:
        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            linkedin_id=linkedin_id,
            name=name,
            email=email,
            access_token=token['access_token']
        ).save()
    else:
        # Update existing user
        user.access_token = token['access_token']
        if name:
            user.name = name
        if email:
            user.email = email
        user.save()
    
    # Log in the user
    login_user(user)
    
    # Redirect to conversation page
    return redirect(url_for('main.conversations'))

@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    """Handle client connect"""
    if current_user.is_authenticated:
        # Join a room specific to this user
        socketio.emit('user_connected', {'user_id': current_user.id})
