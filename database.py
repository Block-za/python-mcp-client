"""
Database configuration and models for the chat application.
Handles PostgreSQL connection and provides ORM models for conversations and messages.
"""

import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

# Initialize SQLAlchemy
db = SQLAlchemy()

class Conversation(db.Model):
    """Model for conversations table"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to messages
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert conversation to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'message_count': len(self.messages)
        }

class Message(db.Model):
    """Model for messages table"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    is_summary = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        """Convert message to dictionary"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'is_summary': self.is_summary
        }

def init_database(app):
    """Initialize database with Flask app"""
    # Database configuration with better debugging
    database_url = os.getenv('DATABASE_URL')
    
    # Debug environment variables
    print("🔍 Database Configuration Debug:")
    print(f"DATABASE_URL found: {'✅' if database_url else '❌'}")
    if database_url:
        print(f"DATABASE_URL: {database_url[:50]}...")
    else:
        print("❌ DATABASE_URL not found in environment!")
        print("Available environment variables:")
        for key in sorted(os.environ.keys()):
            if any(term in key.upper() for term in ['DATABASE', 'DB_', 'SUPABASE', 'POSTGRES']):
                value = os.environ[key]
                # Mask passwords
                if 'PASSWORD' in key.upper() or 'SECRET' in key.upper():
                    value = '*' * len(value)
                elif len(value) > 50:
                    value = value[:50] + '...'
                print(f"  {key}: {value}")
    
    if not database_url:
        # Fallback to local PostgreSQL
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'chat_app')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        
        database_url = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
        print(f"⚠️ Using fallback database: {database_url}")
    else:
        print(f"✅ Using configured database: {database_url[:50]}...")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        try:
            # Test connection first with a simple query
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db.create_all()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("⚠️  App will start without database (limited functionality)")
            # Don't raise - let the app start anyway
            # Users will see connection errors when trying to save conversations

def get_conversations_by_email(email, limit=50):
    """Get all conversations for a user by email"""
    return Conversation.query.filter_by(email=email)\
                           .order_by(Conversation.updated_at.desc())\
                           .limit(limit).all()

def create_conversation(email, title):
    """Create a new conversation"""
    conversation = Conversation(email=email, title=title)
    db.session.add(conversation)
    db.session.commit()
    return conversation

def get_conversation_by_id(conversation_id, email=None):
    """Get a conversation by ID, optionally filtered by email"""
    query = Conversation.query.filter_by(id=conversation_id)
    if email:
        query = query.filter_by(email=email)
    return query.first()

def add_message(conversation_id, role, content, is_summary=False):
    """Add a message to a conversation"""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        is_summary=is_summary
    )
    db.session.add(message)
    
    # Update conversation's updated_at timestamp
    conversation = Conversation.query.get(conversation_id)
    if conversation:
        conversation.updated_at = datetime.utcnow()
    
    db.session.commit()
    return message

def get_messages_for_context(conversation_id, limit=10):
    """
    Get messages for context building.
    Returns the most recent summary (if any) + last N messages.
    """
    try:
        # Get the most recent summary
        latest_summary = Message.query.filter_by(
            conversation_id=conversation_id,
            role='system',
            is_summary=True
        ).order_by(Message.timestamp.desc()).first()
        
        # Get the last N messages (excluding summaries)
        recent_messages = Message.query.filter_by(conversation_id=conversation_id)\
                                      .filter(Message.is_summary == False)\
                                      .order_by(Message.timestamp.desc())\
                                      .limit(limit).all()
        
        # Reverse to get chronological order
        recent_messages.reverse()
        
        # Combine summary and recent messages
        context_messages = []
        if latest_summary:
            context_messages.append(latest_summary)
        context_messages.extend(recent_messages)
        
        return context_messages
    except Exception as e:
        print(f"Error in get_messages_for_context: {e}")
        return []

def get_all_messages_for_conversation(conversation_id):
    """Get all messages for a conversation (for display)"""
    try:
        return Message.query.filter_by(conversation_id=conversation_id)\
                           .order_by(Message.timestamp.asc()).all()
    except Exception as e:
        print(f"Error in get_all_messages_for_conversation: {e}")
        return []

def should_summarize_conversation(conversation_id, threshold=20):
    """
    Check if a conversation should be summarized based on message count.
    Returns True if the conversation has more than threshold messages.
    """
    message_count = Message.query.filter_by(conversation_id=conversation_id).count()
    return message_count > threshold

def create_conversation_summary(conversation_id, summary_content):
    """
    Create a summary message for a conversation.
    This replaces older messages with a system message containing the summary.
    """
    # Add the summary as a system message
    summary_message = add_message(conversation_id, 'system', summary_content, is_summary=True)
    
    # Optionally, you could delete old messages here to save space
    # For now, we'll keep them but mark them as summarized
    
    return summary_message

def delete_conversation(conversation_id, email=None):
    """
    Delete a conversation and all its messages.
    If email is provided, ensures the conversation belongs to that user.
    """
    try:
        # Get the conversation
        query = Conversation.query.filter_by(id=conversation_id)
        if email:
            query = query.filter_by(email=email)
        
        conversation = query.first()
        if not conversation:
            return False, "Conversation not found"
        
        # Delete the conversation (messages will be deleted automatically due to cascade)
        db.session.delete(conversation)
        db.session.commit()
        
        return True, "Conversation deleted successfully"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error deleting conversation: {str(e)}"