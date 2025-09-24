class AudioManager {
    constructor(app) {
        this.app = app;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.audioContext = null;
        this.analyser = null;
        this.audioPlayer = document.getElementById('audio-player');
        
        this.init();
    }
    
    init() {
        // 检查浏览器兼容性
        this.checkBrowserSupport();
        
        // 初始化音频播放器
        this.initAudioPlayer();
    }
    
    checkBrowserSupport() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.warn('浏览器不支持语音录制功能');
            this.disableVoiceFeatures();
            return false;
        }
        
        if (!window.MediaRecorder) {
            console.warn('浏览器不支持MediaRecorder');
            this.disableVoiceFeatures();
            return false;
        }
        
        return true;
    }
    
    disableVoiceFeatures() {
        const voiceBtn = document.getElementById('voice-btn');
        if (voiceBtn) {
            voiceBtn.disabled = true;
            voiceBtn.innerHTML = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" opacity="0.5"/>
                    <path d="M19 11a7 7 0 0 1-14 0" opacity="0.5"/>
                    <path d="M12 18.5v3" opacity="0.5"/>
                    <path d="M8 22h8" opacity="0.5"/>
                </svg>
                浏览器不支持
            `;
        }
    }
    
    initAudioPlayer() {
        if (this.audioPlayer) {
            this.audioPlayer.addEventListener('ended', () => {
                console.log('音频播放完成');
            });
            
            this.audioPlayer.addEventListener('error', (e) => {
                console.error('音频播放错误:', e);
            });
        }
    }
    
    async startRecording() {
        if (!this.checkBrowserSupport()) {
            return false;
        }
        
        try {
            // 请求麦克风权限
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000
                }
            });
            
            // 创建MediaRecorder
            const options = {
                mimeType: this.getSupportedMimeType(),
                audioBitsPerSecond: 128000
            };
            
            this.mediaRecorder = new MediaRecorder(this.stream, options);
            this.audioChunks = [];
            
            // 设置事件监听器
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.processRecording();
            };
            
            this.mediaRecorder.onerror = (event) => {
                console.error('录音错误:', event);
                this.stopRecording();
            };
            
            // 开始录音
            this.mediaRecorder.start();
            this.isRecording = true;
            
            // 初始化音频可视化
            this.initAudioVisualization();
            
            // 更新UI
            this.updateRecordingUI(true);
            
            return true;
            
        } catch (error) {
            console.error('开始录音失败:', error);
            
            if (error.name === 'NotAllowedError') {
                this.app.showModal('请允许访问麦克风权限以使用语音功能');
            } else if (error.name === 'NotFoundError') {
                this.app.showModal('未找到麦克风设备');
            } else {
                this.app.showModal('无法启动录音功能: ' + error.message);
            }
            
            return false;
        }
    }
    
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            // 停止音频流
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }
            
            // 停止音频可视化
            this.stopAudioVisualization();
            
            // 更新UI
            this.updateRecordingUI(false);
        }
    }
    
    getSupportedMimeType() {
        const types = [
            'audio/wav',
            'audio/webm;codecs=opus',
            'audio/ogg;codecs=opus',
            'audio/mp4',
            'audio/webm'
        ];
        
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }
        
        return '';
    }
    
    initAudioVisualization() {
        if (!this.stream) return;
        
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            
            const source = this.audioContext.createMediaStreamSource(this.stream);
            source.connect(this.analyser);
            
            this.analyser.fftSize = 256;
            const bufferLength = this.analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            
            const visualize = () => {
                if (!this.isRecording) return;
                
                this.analyser.getByteFrequencyData(dataArray);
                
                // 计算音量级别
                const volume = dataArray.reduce((sum, value) => sum + value, 0) / bufferLength;
                
                // 更新波浪动画
                this.updateWaveAnimation(volume);
                
                requestAnimationFrame(visualize);
            };
            
            visualize();
            
        } catch (error) {
            console.error('音频可视化初始化失败:', error);
        }
    }
    
    stopAudioVisualization() {
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
            this.analyser = null;
        }
    }
    
    updateWaveAnimation(volume) {
        const waveElement = document.getElementById('voice-wave');
        if (!waveElement) return;
        
        const bars = waveElement.querySelectorAll('.wave-bar');
        bars.forEach((bar, index) => {
            const height = Math.max(10, (volume / 255) * 30 + Math.random() * 10);
            bar.style.height = height + 'px';
            bar.style.animationDelay = (index * 0.1) + 's';
        });
    }
    
    updateRecordingUI(isRecording) {
        const voiceBtn = document.getElementById('voice-btn');
        const voiceWave = document.getElementById('voice-wave');
        
        if (voiceBtn) {
            if (isRecording) {
                voiceBtn.classList.add('recording');
                voiceBtn.innerHTML = `
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                        <rect x="6" y="6" width="12" height="12" rx="2"/>
                    </svg>
                    点击停止
                `;
            } else {
                voiceBtn.classList.remove('recording');
                voiceBtn.innerHTML = `
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
                        <path d="M19 11a7 7 0 0 1-14 0"/>
                        <path d="M12 18.5v3"/>
                        <path d="M8 22h8"/>
                    </svg>
                    点击说话
                `;
            }
        }
        
        if (voiceWave) {
            voiceWave.style.display = isRecording ? 'flex' : 'none';
        }
    }
    
    async processRecording() {
        if (this.audioChunks.length === 0) {
            console.warn('没有录音数据');
            return;
        }
        
        try {
            // 创建音频Blob
            const audioBlob = new Blob(this.audioChunks, { 
                type: this.getSupportedMimeType() || 'audio/wav' 
            });
            
            // 转换为base64
            const audioBase64 = await this.blobToBase64(audioBlob);
            
            // 发送语音聊天请求
            await this.sendVoiceMessage(audioBase64);
            
        } catch (error) {
            console.error('处理录音失败:', error);
            this.app.showModal('语音处理失败，请重试');
        }
    }
    
    async blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const dataUrl = reader.result;
                const base64 = dataUrl.split(',')[1];
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }
    
    async sendVoiceMessage(audioBase64) {
        if (!this.app.currentCharacter) {
            this.app.showModal('请先选择一个角色');
            return;
        }
        
        // 显示语音处理状态
        const processingId = this.app.addThinkingMessage('正在处理语音...');
        
        try {
            const response = await fetch('/api/audio/voice-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    audio_data: audioBase64,
                    character_id: this.app.currentCharacter.character_id,
                    conversation_id: this.app.currentConversation?.conversation_id,
                    voice: 'zhifeng' // 可以让用户选择
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // 移除处理状态
                this.app.removeThinkingMessage(processingId);
                
                if (result.success) {
                    // 更新当前对话ID
                    if (!this.app.currentConversation) {
                        this.app.currentConversation = { 
                            conversation_id: result.conversation_id 
                        };
                    }
                    
                    // 添加用户语音消息（显示识别的文字）
                    this.app.addMessageToUI('user', result.user_text);
                    
                    // 添加AI回复消息
                    this.app.addMessageToUI('assistant', result.ai_text);
                    
                    // 播放AI语音回复
                    if (result.ai_audio_url) {
                        await this.playAudio(result.ai_audio_url);
                    }
                    
                    // 重新加载对话列表
                    await this.app.loadConversations();
                    
                } else {
                    this.app.addMessageToUI('assistant', '抱歉，语音处理失败: ' + result.error);
                }
            } else {
                this.app.removeThinkingMessage(processingId);
                this.app.addMessageToUI('assistant', '语音消息发送失败');
            }
            
        } catch (error) {
            console.error('发送语音消息失败:', error);
            this.app.removeThinkingMessage(processingId);
            this.app.addMessageToUI('assistant', '网络连接失败，请稍后重试');
        }
    }
    
    async playAudio(audioUrl) {
        if (!this.audioPlayer) {
            console.warn('音频播放器不可用');
            return;
        }
        
        try {
            this.audioPlayer.src = audioUrl;
            
            // 等待音频加载
            await new Promise((resolve, reject) => {
                this.audioPlayer.oncanplaythrough = resolve;
                this.audioPlayer.onerror = reject;
                this.audioPlayer.load();
            });
            
            // 播放音频
            await this.audioPlayer.play();
            
        } catch (error) {
            console.error('音频播放失败:', error);
        }
    }
    
    async textToSpeech(text, voice = 'zhifeng') {
        try {
            const response = await fetch('/api/audio/text-to-speech', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    voice: voice
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.audio_url) {
                    await this.playAudio(result.audio_url);
                    return true;
                }
            }
            
            return false;
            
        } catch (error) {
            console.error('文字转语音失败:', error);
            return false;
        }
    }
    
    // 获取可用音色列表
    async getAvailableVoices() {
        try {
            const response = await fetch('/api/audio/voices');
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    return result.voices;
                }
            }
            return ['zhifeng']; // 默认音色
        } catch (error) {
            console.error('获取音色列表失败:', error);
            return ['zhifeng'];
        }
    }
}

// 扩展主应用类以支持语音功能
if (typeof RoleVerseApp !== 'undefined') {
    // 扩展原有的语音方法
    RoleVerseApp.prototype.initAudio = function() {
        this.audioManager = new AudioManager(this);
    };
    
    RoleVerseApp.prototype.toggleVoiceRecording = async function() {
        if (!this.audioManager) {
            this.initAudio();
        }
        
        if (this.audioManager.isRecording) {
            this.audioManager.stopRecording();
        } else {
            await this.audioManager.startRecording();
        }
    };
    
    // 重写原有的init方法以包含音频初始化
    const originalInit = RoleVerseApp.prototype.init;
    RoleVerseApp.prototype.init = async function() {
        await originalInit.call(this);
        this.initAudio();
    };
}