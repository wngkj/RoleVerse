class RoleVerseApp {
    constructor() {
        this.currentUser = null;
        this.currentCharacter = null;
        this.currentConversation = null;
        this.conversations = [];
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.inputMode = 'voice'; // 'voice' 或 'text'
        
        this.init();
    }
    
    async init() {
        console.log('初始化RoleVerseApp...');
        
        // 检查登录状态
        await this.checkAuth();
        
        // 初始化UI组件
        this.initUI();
        
        // 绑定事件
        this.bindEvents();
        
        // 加载数据
        await this.loadInitialData();
        
        console.log('RoleVerseApp初始化完成');
    }
    
    async checkAuth() {
        try {
            const response = await fetch('/api/user/info');
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.currentUser = result.user;
                    this.updateUserInfo();
                } else {
                    this.redirectToLogin();
                }
            } else {
                this.redirectToLogin();
            }
        } catch (error) {
            console.error('检查登录状态失败:', error);
            this.redirectToLogin();
        }
    }
    
    redirectToLogin() {
        window.location.href = '/login';
    }
    
    updateUserInfo() {
        const usernameElement = document.getElementById('username');
        const logoutBtn = document.getElementById('logout-btn');
        
        if (this.currentUser) {
            usernameElement.textContent = this.currentUser.username;
            logoutBtn.style.display = 'inline-block';
        }
    }
    
    initUI() {
        // 初始化语音输入
        this.initVoiceInput();
        
        // 初始化输入模式切换
        this.initInputModeToggle();
        
        // 初始化搜索功能
        this.initSearch();
        
        // 初始化对话功能
        this.initChat();
    }
    
    initVoiceInput() {
        // 检查浏览器是否支持语音录制
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.warn('浏览器不支持语音录制功能');
            // 如果不支持语音，默认切换到文字模式
            this.inputMode = 'text';
            return;
        }
    }
    
    initInputModeToggle() {
        const voiceModeBtn = document.getElementById('voice-mode-btn');
        const textModeBtn = document.getElementById('text-mode-btn');
        
        if (voiceModeBtn && textModeBtn) {
            voiceModeBtn.addEventListener('click', () => {
                this.switchInputMode('voice');
            });
            
            textModeBtn.addEventListener('click', () => {
                this.switchInputMode('text');
            });
        }
        
        // 初始化默认模式
        this.switchInputMode(this.inputMode);
    }
    
    switchInputMode(mode) {
        this.inputMode = mode;
        
        const voiceModeBtn = document.getElementById('voice-mode-btn');
        const textModeBtn = document.getElementById('text-mode-btn');
        const voiceContainer = document.getElementById('voice-input-container');
        const textContainer = document.getElementById('text-input-container');
        
        // 更新按钮状态
        if (voiceModeBtn && textModeBtn) {
            voiceModeBtn.classList.toggle('active', mode === 'voice');
            textModeBtn.classList.toggle('active', mode === 'text');
        }
        
        // 显示/隐藏对应的输入容器
        if (voiceContainer && textContainer) {
            voiceContainer.style.display = mode === 'voice' ? 'block' : 'none';
            textContainer.style.display = mode === 'text' ? 'flex' : 'none';
        }
        
        console.log(`切换到${mode === 'voice' ? '语音' : '文字'}输入模式`);
    }
    
    initSearch() {
        const searchInput = document.getElementById('character-search');
        const searchBtn = document.getElementById('search-btn');
        
        console.log('初始化搜索功能:', {
            searchInput: !!searchInput,
            searchBtn: !!searchBtn
        });
        
        if (!searchInput || !searchBtn) {
            console.error('搜索相关元素未找到');
            return;
        }
        
        // 防抖搜索
        let searchTimeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = searchInput.value.trim();
                console.log('输入搜索:', query);
                if (query.length > 0) {
                    this.searchCharacters(query);
                } else {
                    this.hideSearchResults();
                }
            }, 300);
        });
        
        searchBtn.addEventListener('click', () => {
            const query = searchInput.value.trim();
            console.log('点击搜索按钮:', query);
            if (query) {
                this.searchCharacters(query);
            }
        });
        
        // 回车搜索
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = searchInput.value.trim();
                console.log('回车搜索:', query);
                if (query) {
                    this.searchCharacters(query);
                }
            }
        });
    }
    
    initChat() {
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        if (sendBtn) {
            sendBtn.addEventListener('click', () => {
                this.sendMessage();
            });
        }
    }
    
    bindEvents() {
        // 登出按钮
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.logout();
            });
        }
        
        // 语音按钮
        const voiceBtn = document.getElementById('voice-btn');
        if (voiceBtn) {
            voiceBtn.addEventListener('click', () => {
                this.toggleVoiceRecording();
            });
        }
        
        // 模态框关闭
        const modalClose = document.getElementById('modal-close');
        const modal = document.getElementById('modal');
        
        if (modalClose && modal) {
            modalClose.addEventListener('click', () => {
                modal.style.display = 'none';
            });
            
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        }
    }
    
    async loadInitialData() {
        // 加载对话列表
        await this.loadConversations();
        
        // 不再加载默认角色，始终显示搜索界面
        this.showSearchInterface();
    }
    
    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.conversations = result.conversations;
                    this.renderConversations();
                }
            }
        } catch (error) {
            console.error('加载对话列表失败:', error);
        }
    }
    
    renderConversations() {
        const container = document.getElementById('conversations-container');
        if (!container) return;
        
        // 按角色分组对话
        const groupedConversations = {};
        this.conversations.forEach(conv => {
            const characterName = conv.character_name;
            if (!groupedConversations[characterName]) {
                groupedConversations[characterName] = [];
            }
            groupedConversations[characterName].push(conv);
        });
        
        // 渲染分组对话
        let html = '';
        Object.keys(groupedConversations).forEach(characterName => {
            const conversations = groupedConversations[characterName];
            
            html += `
                <div class=\"conversation-group\">
                    <div class=\"character-header\" onclick=\"app.toggleCharacterConversations('${characterName}')\">
                        <img src=\"/static/images/default-avatar.png\" alt=\"${characterName}\">
                        <span class=\"character-name\">${characterName}</span>
                    </div>
                    <div class=\"character-conversations\" id=\"conversations-${characterName}\" style=\"display: none;\">
            `;
            
            conversations.forEach(conv => {
                html += `
                    <div class="conversation-item">
                        <div class="conversation-content" onclick="app.openConversation('${conv.conversation_id}')">
                            <div class="conversation-title">${conv.title}</div>
                            <div class="conversation-preview">${conv.last_message || '暂无消息'}</div>
                        </div>
                        <button class="delete-btn" onclick="event.stopPropagation(); app.deleteConversation('${conv.conversation_id}')" title="删除对话">
                            ×
                        </button>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    toggleCharacterConversations(characterName) {
        const element = document.getElementById(`conversations-${characterName}`);
        if (element) {
            element.style.display = element.style.display === 'none' ? 'block' : 'none';
        }
    }
    
    async openConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}`);
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.currentConversation = result.conversation;
                    
                    // 加载角色信息
                    await this.loadCharacterInfo(this.currentConversation.character_id);
                    
                    // 显示聊天界面
                    this.showChatInterface();
                    
                    // 渲染消息
                    this.renderMessages();
                }
            }
        } catch (error) {
            console.error('打开对话失败:', error);
        }
    }
    
    async loadCharacterInfo(characterId) {
        try {
            const response = await fetch(`/api/characters/${characterId}`);
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.currentCharacter = result.character;
                    this.updateCharacterDisplay();
                }
            }
        } catch (error) {
            console.error('加载角色信息失败:', error);
        }
    }
    
    updateCharacterDisplay() {
        if (!this.currentCharacter) return;
        
        const nameElement = document.getElementById('character-name');
        const descElement = document.getElementById('character-description');
        const avatarElement = document.getElementById('character-avatar');
        
        if (nameElement) nameElement.textContent = this.currentCharacter.name;
        if (descElement) descElement.textContent = this.currentCharacter.description;
        if (avatarElement) {
            avatarElement.src = this.currentCharacter.avatar_url || '/static/images/default-avatar.png';
            avatarElement.alt = this.currentCharacter.name;
        }
    }
    
    showChatInterface() {
        const characterDisplay = document.getElementById('character-display');
        const chatContainer = document.getElementById('chat-container');
        const searchResults = document.getElementById('search-results');
        
        if (characterDisplay) characterDisplay.style.display = 'none';
        if (searchResults) searchResults.style.display = 'none';
        if (chatContainer) chatContainer.style.display = 'flex';
    }
    
    showSearchInterface() {
        // 始终显示搜索界面，不显示角色展示区
        const characterDisplay = document.getElementById('character-display');
        const searchResults = document.getElementById('search-results');
        const chatContainer = document.getElementById('chat-container');
        const characterGrid = document.getElementById('character-grid');
        
        if (characterDisplay) characterDisplay.style.display = 'none';
        if (chatContainer) chatContainer.style.display = 'none';
        
        if (searchResults && characterGrid) {
            characterGrid.innerHTML = `
                <div class="search-prompt">
                    <h3>🔍 搜索或创建你想要对话的角色</h3>
                    <p>输入任意角色名称，如：哈利波特、钢铁侠、孙悟空等</p>
                    <p><small>如果角色不存在，系统将自动为您创建</small></p>
                </div>
            `;
            searchResults.style.display = 'block';
        }
    }
    
    hideSearchResults() {
        // 不再隐藏搜索结果，而是返回初始搜索界面
        this.showSearchInterface();
    }
    
    renderMessages() {
        const container = document.getElementById('chat-messages');
        if (!container || !this.currentConversation) return;
        
        let html = '';
        this.currentConversation.messages.forEach(message => {
            const isUser = message.role === 'user';
            const avatarSrc = isUser 
                ? '/static/images/user-avatar.svg' 
                : (this.currentCharacter?.avatar_url || '/static/images/default-avatar.svg');
            
            html += `
                <div class=\"message ${message.role}\">
                    <img src=\"${avatarSrc}\" alt=\"头像\" class=\"message-avatar\">
                    <div class=\"message-content\">
                        ${message.content}
                        <div class=\"message-time\">${new Date(message.timestamp).toLocaleTimeString()}</div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
        // 滚动到底部
        container.scrollTop = container.scrollHeight;
    }
    
    async searchCharacters(query) {
        try {
            // 显示加载提示
            this.showSearchLoading();
            
            const response = await fetch(`/api/characters/search?q=${encodeURIComponent(query)}`);
            
            if (response.ok) {
                const result = await response.json();
                
                if (result.success) {
                    this.showSearchResults(result.characters);
                } else {
                    this.hideSearchLoading();
                    this.showModal('搜索失败: ' + result.error);
                }
            } else {
                this.hideSearchLoading();
                this.showModal('搜索请求失败，请检查网络连接');
            }
        } catch (error) {
            this.hideSearchLoading();
            console.error('搜索角色失败:', error);
            this.showModal('搜索出现错误: ' + error.message);
        }
    }
    
    showSearchResults(characters) {
        const searchResults = document.getElementById('search-results');
        const characterDisplay = document.getElementById('character-display');
        const chatContainer = document.getElementById('chat-container');
        const characterGrid = document.getElementById('character-grid');
        
        if (!searchResults || !characterGrid) {
            console.error('缺少必要的页面元素');
            return;
        }
        
        // 隐藏其他界面
        if (characterDisplay) characterDisplay.style.display = 'none';
        if (chatContainer) chatContainer.style.display = 'none';
        
        // 渲染搜索结果
        let html = '';
        characters.forEach(character => {
            html += `
                <div class="character-card" onclick="app.selectCharacter('${character.character_id}')">
                    <img src="${character.avatar_url || '/static/images/default-avatar.svg'}" alt="${character.name}">
                    <h4>${character.name}</h4>
                    <p>${character.description}</p>
                </div>
            `;
        });
        
        characterGrid.innerHTML = html;
        searchResults.style.display = 'block';
    }
    
    showSearchLoading() {
        const searchResults = document.getElementById('search-results');
        const characterDisplay = document.getElementById('character-display');
        const chatContainer = document.getElementById('chat-container');
        const characterGrid = document.getElementById('character-grid');
        
        if (!searchResults || !characterGrid) return;
        
        // 隐藏其他界面
        if (characterDisplay) characterDisplay.style.display = 'none';
        if (chatContainer) chatContainer.style.display = 'none';
        
        // 显示加载状态
        characterGrid.innerHTML = `
            <div class="loading-container">
                <div class="loading"></div>
                <p>正在搜索或创建角色...</p>
            </div>
        `;
        searchResults.style.display = 'block';
    }
    
    hideSearchLoading() {
        const searchResults = document.getElementById('search-results');
        if (searchResults) {
            searchResults.style.display = 'none';
        }
    }
    
    async selectCharacter(characterId) {
        await this.loadCharacterInfo(characterId);
        
        // 查找该角色的现有对话
        const existingConversation = this.conversations.find(conv => 
            conv.character_id === characterId
        );
        
        if (existingConversation) {
            // 如果有现有对话，加载该对话
            await this.openConversation(existingConversation.conversation_id);
        } else {
            // 如果没有现有对话，显示空白聊天界面但不设置对话为null
            this.currentConversation = null;
            this.showChatInterface();
            
            // 清空消息区域，显示欢迎消息
            const chatMessages = document.getElementById('chat-messages');
            if (chatMessages) {
                chatMessages.innerHTML = '<div class="welcome-message">开始与' + this.currentCharacter.name + '的对话吧！</div>';
            }
        }
    }
    
    async sendMessage() {
        if (!this.currentCharacter) {
            this.showModal('请先选择一个角色');
            return;
        }
        
        let message = '';
        
        // 根据当前输入模式获取消息
        if (this.inputMode === 'text') {
            const messageInput = document.getElementById('message-input');
            message = messageInput ? messageInput.value.trim() : '';
            
            if (!message) return;
            
            // 清空输入框
            if (messageInput) messageInput.value = '';
        } else {
            // 语音模式下，消息将由语音识别功能提供
            console.warn('语音消息发送暂未实现');
            return;
        }
        
        // 立即显示用户消息（提升用户体验）
        this.addMessageToUI('user', message);
        
        // 确保对话状态正确
        this.ensureConversationState();
        
        // 使用流式接口发送消息
        try {
            await this.sendStreamMessage(message);
        } catch (error) {
            console.error('发送消息失败:', error);
            this.addMessageToUI('assistant', '网络连接失败，请稍后重试。');
        }
    }
    
    async sendStreamMessage(message) {
        // 显示AI正在思考
        const thinkingId = this.addThinkingMessage();
        
        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    character_id: this.currentCharacter.character_id,
                    message: message,
                    conversation_id: this.currentConversation?.conversation_id,
                    input_mode: this.inputMode // 传递输入模式
                })
            });
            
            if (response.ok) {
                // 移除思考消息
                this.removeThinkingMessage(thinkingId);
                
                // 创建空的AI消息容器
                const aiMessageId = this.createStreamingMessage();
                
                // 读取流式响应
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let conversationId = '';
                let aiContent = '';
                let audioData = null; // 音频数据
                
                while (true) {
                    const { done, value } = await reader.read();
                    
                    if (done) {
                        break;
                    }
                    
                    buffer += decoder.decode(value, { stream: true });
                    
                    // 处理缓冲区中的数据
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // 保留未完整的行
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.substring(6));
                                
                                if (data.type === 'start') {
                                    conversationId = data.conversation_id;
                                } else if (data.type === 'audio') {
                                    // 保存音频数据
                                    audioData = data.audio_data;
                                } else if (data.type === 'chunk') {
                                    aiContent += data.content;
                                    this.updateStreamingMessage(aiMessageId, aiContent);
                                } else if (data.type === 'end') {
                                    // 流式输出完成
                                    console.log('流式输出完成');
                                    
                                    // 如果有音频数据且在语音模式下，播放音频
                                    if (audioData && this.inputMode === 'voice' && this.audioManager) {
                                        await this.audioManager.playAudioFromBase64(audioData);
                                    }
                                } else if (data.type === 'error') {
                                    throw new Error(data.error);
                                }
                            } catch (e) {
                                console.error('解析SSE数据失败:', e);
                            }
                        }
                    }
                }
                
                // 更新本地对话状态
                if (conversationId && aiContent) {
                    this.currentConversation.conversation_id = conversationId;
                    this.updateLocalConversationState(message, aiContent, conversationId);
                    
                    // 异步刷新对话列表
                    this.loadConversations().catch(console.error);
                }
                
            } else {
                this.removeThinkingMessage(thinkingId);
                this.addMessageToUI('assistant', '抱歉，我现在无法回复您的消息。');
            }
        } catch (error) {
            this.removeThinkingMessage(thinkingId);
            console.error('流式聊天失败:', error);
            this.addMessageToUI('assistant', '网络连接失败，请稍后重试。');
        }
    }
    
    addMessageToUI(role, content) {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        
        const isUser = role === 'user';
        const avatarSrc = isUser 
            ? '/static/images/user-avatar.svg' 
            : (this.currentCharacter?.avatar_url || '/static/images/default-avatar.svg');
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${role}`;
        messageElement.innerHTML = `
            <img src=\"${avatarSrc}\" alt=\"头像\" class=\"message-avatar\">
            <div class=\"message-content\">
                ${content}
                <div class=\"message-time\">${new Date().toLocaleTimeString()}</div>
            </div>
        `;
        
        container.appendChild(messageElement);
        
        // 滚动到底部
        container.scrollTop = container.scrollHeight;
    }
    
    createStreamingMessage() {
        const container = document.getElementById('chat-messages');
        if (!container) return null;
        
        const messageId = 'streaming-' + Date.now();
        const avatarSrc = this.currentCharacter?.avatar_url || '/static/images/default-avatar.svg';
        
        const messageElement = document.createElement('div');
        messageElement.id = messageId;
        messageElement.className = 'message assistant';
        messageElement.innerHTML = `
            <img src=\"${avatarSrc}\" alt=\"头像\" class=\"message-avatar\">
            <div class=\"message-content\">
                <div class=\"streaming-content\"></div>
                <div class=\"message-time\">${new Date().toLocaleTimeString()}</div>
            </div>
        `;
        
        container.appendChild(messageElement);
        container.scrollTop = container.scrollHeight;
        
        return messageId;
    }
    
    updateStreamingMessage(messageId, content) {
        const messageElement = document.getElementById(messageId);
        if (messageElement) {
            const contentElement = messageElement.querySelector('.streaming-content');
            if (contentElement) {
                contentElement.textContent = content;
                
                // 滚动到底部
                const container = document.getElementById('chat-messages');
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            }
        }
    }
    
    addThinkingMessage() {
        const container = document.getElementById('chat-messages');
        if (!container) return null;
        
        const thinkingId = 'thinking-' + Date.now();
        const messageElement = document.createElement('div');
        messageElement.id = thinkingId;
        messageElement.className = 'message assistant';
        messageElement.innerHTML = `
            <img src=\"${this.currentCharacter?.avatar_url || '/static/images/default-avatar.png'}\" alt=\"头像\" class=\"message-avatar\">
            <div class=\"message-content loading\">
                <div class=\"loading\"></div>
            </div>
        `;
        
        container.appendChild(messageElement);
        container.scrollTop = container.scrollHeight;
        
        return thinkingId;
    }
    
    removeThinkingMessage(thinkingId) {
        if (thinkingId) {
            const element = document.getElementById(thinkingId);
            if (element) {
                element.remove();
            }
        }
    }
    
    showModal(content) {
        const modal = document.getElementById('modal');
        const modalBody = document.getElementById('modal-body');
        
        if (modal && modalBody) {
            modalBody.innerHTML = content;
            modal.style.display = 'block';
        }
    }
    
    async logout() {
        try {
            await fetch('/api/logout', { method: 'POST' });
        } catch (error) {
            console.error('登出请求失败:', error);
        } finally {
            window.location.href = '/login';
        }
    }
    
    // 对话状态管理方法
    ensureConversationState() {
        // 确保当前对话状态正确
        if (!this.currentConversation) {
            this.currentConversation = {
                character_id: this.currentCharacter?.character_id,
                messages: []
            };
        }
        
        if (!this.currentConversation.messages) {
            this.currentConversation.messages = [];
        }
        
        return this.currentConversation;
    }
    
    updateLocalConversationState(userMessage, aiResponse, conversationId) {
        // 更新本地对话状态，与后端保持一致
        const conversation = this.ensureConversationState();
        
        // 设置conversation_id
        conversation.conversation_id = conversationId;
        
        // 添加消息到本地对话记录（仅作为本地状态管理）
        conversation.messages.push({
            role: 'user',
            content: userMessage,
            timestamp: new Date().toISOString()
        });
        
        conversation.messages.push({
            role: 'assistant',
            content: aiResponse,
            timestamp: new Date().toISOString()
        });
        
        console.log('本地对话状态已更新:', {
            conversationId,
            messageCount: conversation.messages.length,
            lastMessage: aiResponse.substring(0, 50) + '...'
        });
    }
    
    // 添加删除对话的方法
    async deleteConversation(conversationId) {
        if (!confirm('确定要删除这个对话吗？删除后无法恢复。')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    // 如果删除的是当前对话，返回搜索界面
                    if (this.currentConversation && this.currentConversation.conversation_id === conversationId) {
                        this.currentConversation = null;
                        this.currentCharacter = null;
                        this.showSearchInterface();
                    }
                    
                    // 刷新对话列表
                    await this.loadConversations();
                    this.renderConversations();
                    
                    this.showModal('对话删除成功');
                } else {
                    this.showModal('删除失败: ' + result.error);
                }
            } else {
                this.showModal('删除请求失败，请检查网络连接');
            }
        } catch (error) {
            console.error('删除对话失败:', error);
            this.showModal('删除出现错误: ' + error.message);
        }
    }
}

// 全局应用实例
let app;

// DOM加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    app = new RoleVerseApp();
});

// 处理页面可见性变化
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && app) {
        // 页面重新可见时，可以做一些状态检查
        console.log('页面重新激活');
    }
});