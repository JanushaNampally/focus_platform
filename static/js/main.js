/* ============================================================
   FocusTube - Global JavaScript
   ============================================================ */

// Utility Functions
const Utils = {
    // Format duration from seconds
    formatDuration: (seconds) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else if (minutes > 0) {
            return `${minutes}m`;
        } else {
            return `${secs}s`;
        }
    },

    // Format date
    formatDate: (date) => {
        return new Date(date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    // Show notification
    notify: (message, type = 'info', duration = 3000) => {
        const alertClass = `alert alert-${type}`;
        const alertHtml = `
            <div class="${alertClass} alert-dismissible fade show" role="alert" style="position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px;">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = alertHtml;
        document.body.appendChild(tempDiv.firstChild);

        if (duration) {
            setTimeout(() => {
                const alert = document.querySelector('.alert');
                if (alert) alert.remove();
            }, duration);
        }
    },

    // API Call wrapper
    apiCall: async (url, options = {}) => {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': Utils.getCSRFToken()
            }
        };

        const finalOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, finalOptions);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            Utils.notify('An error occurred. Please try again.', 'danger');
            throw error;
        }
    },

    // Get CSRF token
    getCSRFToken: () => {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] ||
               '';
    },

    // Smoothly scroll to element
    scrollToElement: (selector) => {
        const element = document.querySelector(selector);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
};

// Focus Mode Manager
const FocusMode = {
    sessionStart: null,
    sessionTimer: null,
    warningShown: false,

    start: (durationMinutes = 25) => {
        FocusMode.sessionStart = Date.now();
        const durationMs = durationMinutes * 60 * 1000;
        
        document.body.style.overflow = 'hidden';
        
        FocusMode.sessionTimer = setInterval(() => {
            const elapsed = Date.now() - FocusMode.sessionStart;
            const remaining = Math.max(0, durationMs - elapsed);
            
            FocusMode.updateTimer(remaining);
            
            // Show warning at 5 minutes remaining
            if (remaining < 300000 && !FocusMode.warningShown) {
                FocusMode.warningShown = true;
                Utils.notify('⏰ 5 minutes remaining!', 'warning', 5000);
            }
            
            // End session when time is up
            if (remaining === 0) {
                FocusMode.end();
            }
        }, 1000);
    },

    updateTimer: (ms) => {
        const minutes = Math.floor(ms / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);
        const timerDisplay = document.getElementById('focusTimer');
        if (timerDisplay) {
            timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }
    },

    end: () => {
        clearInterval(FocusMode.sessionTimer);
        document.body.style.overflow = 'auto';
        FocusMode.warningShown = false;
        Utils.notify('🎉 Focus session completed! Great job!', 'success');
    },

    exit: () => {
        if (confirm('⚠️ Are you sure you want to exit focus mode? Your streak will be affected.')) {
            FocusMode.end();
            window.location.href = '/dashboard/';
        }
    }
};

// Gamification Manager
const Gamification = {
    updateStreak: async (userId) => {
        try {
            const data = await Utils.apiCall(`/api/user/${userId}/streak/`);
            const streakElement = document.getElementById('streakCount');
            if (streakElement && data.streak) {
                streakElement.textContent = data.streak;
                streakElement.parentElement.classList.add('streak-animation');
            }
        } catch (error) {
            console.error('Error updating streak:', error);
        }
    },

    checkAchievements: async (userId) => {
        try {
            const data = await Utils.apiCall(`/api/user/${userId}/achievements/`);
            if (data.new_achievements && data.new_achievements.length > 0) {
                data.new_achievements.forEach(badge => {
                    Utils.notify(`🏆 Unlocked: ${badge.name}!`, 'success', 4000);
                });
            }
        } catch (error) {
            console.error('Error checking achievements:', error);
        }
    }
};

// Video Manager
const VideoManager = {
    loadRecommendations: async (topicId = null) => {
        try {
            const url = topicId ? 
                `/api/videos/recommended/?topic_id=${topicId}` :
                '/api/videos/recommended/';
            
            const data = await Utils.apiCall(url);
            VideoManager.renderVideos(data.videos);
        } catch (error) {
            console.error('Error loading recommendations:', error);
        }
    },

    renderVideos: (videos) => {
        const container = document.getElementById('videoFeed');
        if (!container) return;

        container.innerHTML = videos.map(video => `
            <div class="video-card fade-in">
                <div class="video-thumbnail">
                    <img src="${video.thumbnail_url}" alt="${video.title}" loading="lazy">
                    <span class="video-duration">${Utils.formatDuration(video.duration_seconds)}</span>
                    <span class="ai-score-badge">🤖 ${Math.round(video.ai_score)}</span>
                </div>
                <div class="video-info">
                    <h6 class="video-title">${video.title}</h6>
                    <div class="video-meta">
                        <span><i class="fas fa-eye"></i> ${(video.view_count / 1000).toFixed(0)}k</span>
                        <span><i class="fas fa-thumbs-up"></i> ${(video.like_count / 1000).toFixed(1)}k</span>
                    </div>
                    <div class="video-channel">
                        <div class="channel-avatar">${video.channel_name.charAt(0)}</div>
                        <div style="flex: 1;">
                            <small class="d-block">${video.channel_name}</small>
                        </div>
                    </div>
                    <div class="video-actions">
                        <button class="btn-watch" onclick="VideoManager.watchVideo(${video.id})">
                            <i class="fas fa-play"></i> Watch
                        </button>
                        <button class="btn btn-outline-secondary" onclick="VideoManager.saveVideo(${video.id})">
                            <i class="fas fa-bookmark"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    },

    watchVideo: (videoId) => {
        window.location.href = `/videos/${videoId}/watch/`;
    },

    saveVideo: async (videoId) => {
        try {
            await Utils.apiCall(`/api/videos/${videoId}/save/`, {
                method: 'POST'
            });
            Utils.notify('📌 Video saved!', 'success', 2000);
        } catch (error) {
            console.error('Error saving video:', error);
        }
    }
};

// Initialize on document ready
document.addEventListener('DOMContentLoaded', () => {
    // Prevent accidental page navigation in focus mode
    window.addEventListener('beforeunload', (e) => {
        const focusMode = document.body.classList.contains('focus-mode-active');
        if (focusMode) {
            e.preventDefault();
            e.returnValue = 'Are you sure you want to leave focus mode?';
            return 'Are you sure?';
        }
    });

    // Load recommendations if video feed exists
    const videoFeed = document.getElementById('videoFeed');
    if (videoFeed) {
        const topicId = videoFeed.dataset.topicId || null;
        VideoManager.loadRecommendations(topicId);
    }

    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(el => new bootstrap.Tooltip(el));
});

// Export for global use
window.Utils = Utils;
window.FocusMode = FocusMode;
window.Gamification = Gamification;
window.VideoManager = VideoManager;
