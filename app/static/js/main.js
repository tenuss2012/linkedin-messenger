// LinkedIn Messenger - Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Check if notifications are supported
    if ('Notification' in window) {
        // Request permission for notifications
        if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    }

    // Initialize Socket.IO if available
    if (typeof io !== 'undefined') {
        initializeSocketIO();
    }
});

/**
 * Initialize Socket.IO connection and event handlers
 */
function initializeSocketIO() {
    // Reference to the socket (will be set in the individual pages)
    window.messenger = {
        socket: null,
        notifications: {
            enabled: true,
            sound: true
        },
        unreadCount: 0
    };

    // Set page title with unread count
    function updatePageTitle() {
        if (window.messenger.unreadCount > 0) {
            document.title = `(${window.messenger.unreadCount}) LinkedIn Messenger`;
        } else {
            document.title = 'LinkedIn Messenger';
        }
    }

    // Connect to Socket.IO and handle events
    window.messenger.connectSocket = function() {
        if (window.messenger.socket) {
            return; // Already connected
        }

        const socket = io();
        window.messenger.socket = socket;

        socket.on('connect', function() {
            console.log('Connected to real-time messaging server');
        });

        socket.on('disconnect', function() {
            console.log('Disconnected from messaging server');
        });

        socket.on('new_message', function(message) {
            // Handle real-time messages
            console.log('New message received:', message);
            
            // If the current page is the conversations page, the event will be handled there
            // Otherwise, we show a notification
            if (!document.getElementById('conversation-list')) {
                showNotification(message);
            }
        });
    };

    // Show browser notification for new messages
    function showNotification(message) {
        if (!window.messenger.notifications.enabled) {
            return;
        }

        // Increment unread count
        window.messenger.unreadCount++;
        updatePageTitle();

        // Play notification sound if enabled
        if (window.messenger.notifications.sound) {
            playNotificationSound();
        }

        // Show browser notification if permission granted
        if (Notification.permission === 'granted') {
            const notification = new Notification('New LinkedIn Message', {
                body: message.content,
                icon: '/static/img/logo.png'
            });

            notification.onclick = function() {
                window.focus();
                notification.close();
                // Redirect to conversations page if needed
                if (!document.getElementById('conversation-list')) {
                    window.location.href = '/conversations';
                }
            };
        }
    }

    // Play notification sound
    function playNotificationSound() {
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.play();
        } catch (e) {
            console.warn('Could not play notification sound', e);
        }
    }

    // Connect to Socket.IO
    window.messenger.connectSocket();
}

/**
 * Format relative time (e.g., "2 hours ago", "Just now")
 */
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) {
        return 'Just now';
    }
    
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) {
        return `${diffInMinutes}m ago`;
    }
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) {
        return `${diffInHours}h ago`;
    }
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) {
        return `${diffInDays}d ago`;
    }
    
    // Format date as MM/DD/YYYY
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const year = date.getFullYear();
    
    return `${month}/${day}/${year}`;
}

/**
 * Truncate text to a certain length and add ellipsis
 */
function truncateText(text, maxLength = 30) {
    if (!text || text.length <= maxLength) {
        return text;
    }
    return text.substring(0, maxLength) + '...';
}

/**
 * Escape HTML to prevent XSS attacks
 */
function escapeHtml(html) {
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
}
