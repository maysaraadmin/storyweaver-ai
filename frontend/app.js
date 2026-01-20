// PDF Upload Functionality
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for the DOM to be fully ready
    setTimeout(() => {
        const uploadPdfBtn = document.getElementById('upload-pdf-btn');
        const pdfUploadModal = document.getElementById('pdf-upload-modal');
        const closeModal = pdfUploadModal?.querySelector('.close');
        const selectPdfBtn = document.getElementById('select-pdf-btn');
        const pdfFileInput = document.getElementById('pdf-file');
        const selectedFileName = document.getElementById('selected-file-name');
        const confirmUploadBtn = document.getElementById('confirm-upload-btn');
        const cancelUploadBtn = document.getElementById('cancel-upload-btn');
        const uploadProgress = document.getElementById('upload-progress');
        const progressBar = document.querySelector('.progress');
        const uploadStatus = document.getElementById('upload-status');

        console.log('PDF Upload elements:', {
            uploadPdfBtn,
            pdfUploadModal,
            selectPdfBtn,
            pdfFileInput
        });

        // Open modal when upload button is clicked
        if (uploadPdfBtn) {
            uploadPdfBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Upload PDF button clicked');
                if (pdfUploadModal) {
                    pdfUploadModal.style.display = 'block';
                }
            });
        } else {
            console.error('Upload PDF button not found');
        }

        // Close modal when X is clicked
        if (closeModal) {
            closeModal.addEventListener('click', () => {
                if (pdfUploadModal) {
                    pdfUploadModal.style.display = 'none';
                }
            });
        }

        // Close modal when clicking outside the modal
        window.addEventListener('click', (event) => {
            if (event.target === pdfUploadModal) {
                pdfUploadModal.style.display = 'none';
            }
        });

        // Handle file selection
        if (selectPdfBtn) {
            selectPdfBtn.addEventListener('click', () => {
                if (pdfFileInput) {
                    pdfFileInput.click();
                }
            });
        }

        if (pdfFileInput) {
            pdfFileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    if (selectedFileName) {
                        selectedFileName.textContent = file.name;
                    }
                    if (confirmUploadBtn) {
                        confirmUploadBtn.disabled = false;
                    }
                } else {
                    if (selectedFileName) {
                        selectedFileName.textContent = 'No file selected';
                    }
                    if (confirmUploadBtn) {
                        confirmUploadBtn.disabled = true;
                    }
                }
            });
        }

        // Handle upload confirmation
        if (confirmUploadBtn) {
            confirmUploadBtn.addEventListener('click', async () => {
                const file = pdfFileInput?.files[0];
                if (!file) return;

                const formData = new FormData();
                formData.append('file', file);

                try {
                    // Show progress
                    if (uploadProgress) {
                        uploadProgress.style.display = 'block';
                    }
                    if (confirmUploadBtn) {
                        confirmUploadBtn.disabled = true;
                    }
                    if (cancelUploadBtn) {
                        cancelUploadBtn.disabled = true;
                    }

                    // Upload the file
                    const response = await fetch('/api/upload-pdf/', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        throw new Error('Upload failed: ' + response.statusText);
                    }

                    const data = await response.json();
                    
                    // Update UI to show success
                    if (progressBar) {
                        progressBar.style.width = '100%';
                    }
                    if (uploadStatus) {
                        uploadStatus.textContent = 'Upload successful! Loading story...';
                    }

                    // Reload the page to show the new story
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);

                } catch (error) {
                    console.error('Error uploading PDF:', error);
                    if (uploadStatus) {
                        uploadStatus.textContent = 'Error: ' + error.message;
                        uploadStatus.style.color = 'red';
                    }
                } finally {
                    if (confirmUploadBtn) {
                        confirmUploadBtn.disabled = false;
                    }
                    if (cancelUploadBtn) {
                        cancelUploadBtn.disabled = false;
                    }
                }
            });
        }

        // Handle cancel upload
        if (cancelUploadBtn) {
            cancelUploadBtn.addEventListener('click', () => {
                // Reset the form
                if (pdfFileInput) {
                    pdfFileInput.value = '';
                }
                if (selectedFileName) {
                    selectedFileName.textContent = 'No file selected';
                }
                if (uploadProgress) {
                    uploadProgress.style.display = 'none';
                }
                if (progressBar) {
                    progressBar.style.width = '0%';
                }
                if (uploadStatus) {
                    uploadStatus.textContent = 'Uploading...';
                    uploadStatus.style.color = '';
                }
                if (confirmUploadBtn) {
                    confirmUploadBtn.disabled = true;
                }
                
                // Hide the modal
                if (pdfUploadModal) {
                    pdfUploadModal.style.display = 'none';
                }
            });
        }
    }, 100);
});

class StoryWeaverApp {
    constructor() {
        this.apiBase = 'http://localhost:8000/api';
        this.currentStory = null;
        this.messages = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadStories();
        this.addWelcomeMessage();
    }

    setupEventListeners() {
        // Chat functionality
        const sendBtn = document.getElementById('send-btn');
        const messageInput = document.getElementById('message-input');
        
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }

        // Story selection
        const storyItems = document.querySelectorAll('.story-item');
        storyItems.forEach(item => {
            item.addEventListener('click', () => {
                this.selectStory(item.dataset.id, item.querySelector('span').textContent);
            });
        });

        // Expansion proposal
        const proposeBtn = document.getElementById('propose-expansion-btn');
        const submitExpansionBtn = document.getElementById('submit-expansion-btn');
        const cancelExpansionBtn = document.getElementById('cancel-expansion-btn');
        
        if (proposeBtn) {
            proposeBtn.addEventListener('click', () => this.openExpansionModal());
        }
        
        if (submitExpansionBtn) {
            submitExpansionBtn.addEventListener('click', () => this.submitExpansion());
        }
        
        if (cancelExpansionBtn) {
            cancelExpansionBtn.addEventListener('click', () => this.closeExpansionModal());
        }

        // Clear chat
        const clearChatBtn = document.getElementById('clear-chat-btn');
        if (clearChatBtn) {
            clearChatBtn.addEventListener('click', () => this.clearChat());
        }

        // Modal close button
        const closeBtn = document.querySelector('.close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeExpansionModal());
        }

        // Close modal on outside click
        window.addEventListener('click', (e) => {
            const modal = document.getElementById('expansion-modal');
            if (e.target === modal) {
                this.closeExpansionModal();
            }
        });
    }

    async loadStories() {
        try {
            const response = await fetch(this.apiBase + '/stories');
            const data = await response.json();
            
            // The API returns {stories: [...]} directly
            if (data && data.stories) {
                this.populateStoriesList(data.stories);
            } else {
                console.error('Failed to load stories: Invalid response format');
                this.showError('Failed to load stories. Please try again.');
            }
        } catch (error) {
            console.error('Error loading stories:', error);
            this.showError('Failed to load stories. Please try again.');
        }
    }

    populateStoriesList(stories) {
        const storiesList = document.getElementById('stories-list');
        if (!storiesList) return;

        storiesList.innerHTML = '';
        
        stories.forEach(story => {
            const storyItem = document.createElement('div');
            storyItem.className = 'story-item';
            storyItem.dataset.id = story.id;
            
            const icon = document.createElement('i');
            icon.className = 'fas fa-book';
            
            const span = document.createElement('span');
            span.textContent = story.title;
            
            storyItem.appendChild(icon);
            storyItem.appendChild(span);
            
            storyItem.addEventListener('click', () => {
                this.selectStory(story.id, story.title);
            });
            
            storiesList.appendChild(storyItem);
        });
    }

    selectStory(storyId, storyTitle) {
        this.currentStory = { id: storyId, title: storyTitle };
        
        // Update UI to show selected story
        document.querySelectorAll('.story-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        const selectedItem = document.querySelector('[data-id="' + storyId + '"]');
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }
        
        this.addSystemMessage('Selected story: ' + storyTitle);
        this.loadStoryLogic(storyId);
    }

    async loadStoryLogic(storyId) {
        try {
            const response = await fetch(this.apiBase + '/stories/' + storyId);
            const data = await response.json();
            
            if (data.success) {
                this.updateStoryLogicPanel(data.data);
            }
        } catch (error) {
            console.error('Error loading story logic:', error);
        }
    }

    updateStoryLogicPanel(storyData) {
        const charactersList = document.getElementById('characters-list');
        const locationsList = document.getElementById('locations-list');
        const rulesList = document.getElementById('rules-list');
        
        if (charactersList && storyData.elements) {
            charactersList.innerHTML = '';
            storyData.elements
                .filter(el => el.type === 'character')
                .forEach(el => {
                    const li = document.createElement('li');
                    li.textContent = el.name + ' (' + el.description + ')';
                    charactersList.appendChild(li);
                });
        }
        
        if (locationsList && storyData.elements) {
            locationsList.innerHTML = '';
            storyData.elements
                .filter(el => el.type === 'location')
                .forEach(el => {
                    const li = document.createElement('li');
                    li.textContent = el.name;
                    locationsList.appendChild(li);
                });
        }
        
        if (rulesList) {
            rulesList.innerHTML = '<li>Story consistency rules will be shown here</li>';
        }
    }

    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        if (!this.currentStory) {
            this.showError('Please select a story first.');
            return;
        }
        
        // Add user message to chat
        this.addMessage(message, 'user');
        messageInput.value = '';
        
        // Show loading indicator
        this.showLoading();
        
        try {
            const response = await fetch(this.apiBase + '/stories/' + this.currentStory.id + '/messages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: message,
                    sender: 'user'
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // The bot response is automatically added by the backend
                // Reload messages to get the bot's response
                setTimeout(() => {
                    this.loadMessages();
                }, 500);
            } else {
                this.showError('Failed to send message. Please try again.');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message. Please check your connection.');
        } finally {
            this.hideLoading();
        }
    }

    async loadMessages() {
        if (!this.currentStory) return;
        
        try {
            const response = await fetch(this.apiBase + '/stories/' + this.currentStory.id + '/messages');
            const messages = await response.json();
            
            // Clear existing messages and reload them
            const messagesContainer = document.getElementById('chat-messages');
            if (messagesContainer) {
                // Keep only the welcome message
                const welcomeMsg = messagesContainer.querySelector('.message.bot');
                messagesContainer.innerHTML = '';
                if (welcomeMsg) {
                    messagesContainer.appendChild(welcomeMsg);
                }
                
                // Add all messages
                messages.forEach(msg => {
                    this.addMessage(msg.content, msg.sender);
                });
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }

    addMessage(text, sender) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ' + sender;
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.innerHTML = sender === 'bot' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';
        
        const content = document.createElement('div');
        content.className = 'content';
        
        const name = document.createElement('div');
        name.className = 'name';
        name.textContent = sender === 'bot' ? 'StoryBot' : 'You';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'text';
        textDiv.textContent = text;
        
        content.appendChild(name);
        content.appendChild(textDiv);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        this.messages.push({ text: text, sender: sender, timestamp: new Date() });
    }

    addWelcomeMessage() {
        this.addMessage('Hello! I\'m here to help you explore and expand children\'s stories. Please select a story to begin.', 'bot');
    }

    addSystemMessage(text) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
        
        const systemDiv = document.createElement('div');
        systemDiv.className = 'system-message';
        systemDiv.textContent = text;
        
        messagesContainer.appendChild(systemDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    openExpansionModal() {
        if (!this.currentStory) {
            this.showError('Please select a story first.');
            return;
        }
        
        const modal = document.getElementById('expansion-modal');
        if (modal) {
            modal.style.display = 'block';
            document.getElementById('expansion-page').value = '1';
        }
    }

    closeExpansionModal() {
        const modal = document.getElementById('expansion-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    async submitExpansion() {
        const expansionText = document.getElementById('expansion-text').value.trim();
        const pageNumber = parseInt(document.getElementById('expansion-page').value);
        
        if (!expansionText) {
            this.showError('Please enter your expansion idea.');
            return;
        }
        
        try {
            const response = await fetch(this.apiBase + '/propose-expansion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    story_id: this.currentStory.id,
                    new_content: expansionText,
                    page_number: pageNumber,
                    element_references: []
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addMessage('Expansion proposal submitted successfully!', 'bot');
                this.closeExpansionModal();
                document.getElementById('expansion-text').value = '';
            } else {
                this.showError('Failed to submit expansion. Please try again.');
            }
        } catch (error) {
            console.error('Error submitting expansion:', error);
            this.showError('Failed to submit expansion. Please check your connection.');
        }
    }

    clearChat() {
        const messagesContainer = document.getElementById('chat-messages');
        if (messagesContainer) {
            messagesContainer.innerHTML = '';
            this.messages = [];
            this.addWelcomeMessage();
        }
    }

    updatePermissibilityIndicator(isPermissible) {
        const indicator = document.getElementById('permissibility-status');
        if (indicator) {
            if (isPermissible) {
                indicator.className = 'status-permissible';
                indicator.innerHTML = '<i class="fas fa-check-circle"></i> Story Consistent';
            } else {
                indicator.className = 'status-impermissible';
                indicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Story Inconsistent';
            }
        }
    }

    showLoading() {
        const sendBtn = document.getElementById('send-btn');
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
        }
    }

    hideLoading() {
        const sendBtn = document.getElementById('send-btn');
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send';
        }
    }

    showError(message) {
        // Create error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-notification';
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new StoryWeaverApp();
});

// Utility functions
function sanitizeInput(input) {
    const div = document.createElement('div');
    div.textContent = input;
    return div.innerHTML;
}

function formatTimestamp(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
