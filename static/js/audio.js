class AudioManager {
    constructor(app) {
        this.app = app;
        this.isRecording = false;
        this.stream = null;
        this.audioContext = null;
        this.analyser = null;
        this.audioPlayer = document.getElementById('audio-player');
        // 实时语音识别相关属性
        this.recognitionSessionId = null;
        this.audioProcessor = null;
        this.recognizedText = '';
        // 实时语音合成相关属性
        this.isVoiceMode = false; // 是否为语音模式
        this.audioBuffer = null; // 音频缓冲区
        
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
            
            // 初始化音频可视化
            this.initAudioVisualization();
            
            // 更新UI
            this.updateRecordingUI(true);
            
            // 开始实时语音识别
            await this.startRealTimeSpeechRecognition();
            
            this.isRecording = true;
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
        if (this.isRecording) {
            this.isRecording = false;
            
            // 停止实时语音识别
            this.stopRealTimeSpeechRecognition();
            
            // 停止音频处理
            if (this.audioProcessor) {
                this.audioProcessor.disconnect();
                this.audioProcessor = null;
            }
            
            // 关闭音频上下文
            if (this.audioContext) {
                this.audioContext.close();
                this.audioContext = null;
            }
            
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
    
    // 开始实时语音识别
    async startRealTimeSpeechRecognition() {
        try {
            // 调用后端API开始实时语音识别
            const response = await fetch('/api/audio/start-speech-recognition', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    character_id: this.app.currentCharacter?.character_id,
                    conversation_id: this.app.currentConversation?.conversation_id
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    console.log('开始实时语音识别，会话ID:', result.session_id);
                    this.recognitionSessionId = result.session_id;
                    
                    // 开始音频数据流传输
                    this.startAudioStreaming();
                } else {
                    throw new Error(result.error || '无法启动语音识别');
                }
            } else {
                throw new Error('语音识别服务不可用');
            }
        } catch (error) {
            console.error('启动实时语音识别失败:', error);
            this.app.showModal('语音识别启动失败: ' + error.message);
            this.stopRecording();
        }
    }
    
    // 停止实时语音识别
    async stopRealTimeSpeechRecognition() {
        if (this.recognitionSessionId) {
            try {
                // 调用后端API停止语音识别，并获取最终识别文本
                const response = await fetch('/api/audio/stop-speech-recognition', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        session_id: this.recognitionSessionId
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    console.log('停止语音识别结果:', result);
                    if (result.success && result.text) {
                        // 如果有最终识别文本，发送给角色
                        this.onSpeechRecognized(result.text);
                    } else if (result.success) {
                        // 即使没有文本也停止录音
                        this.stopRecording();
                    }
                } else {
                    console.error('停止语音识别失败，状态码:', response.status);
                    this.stopRecording();
                }
            } catch (error) {
                console.error('停止语音识别请求失败:', error);
                this.stopRecording();
            }
            
            this.recognitionSessionId = null;
            console.log('停止实时语音识别');
        }
    }
    
    // 音频流传输方法
    startAudioStreaming() {
        if (!this.stream || !this.recognitionSessionId) return;
        
        try {
            // 创建音频上下文
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });
            
            // 创建音频处理节点
            const source = this.audioContext.createMediaStreamSource(this.stream);
            this.audioProcessor = this.audioContext.createScriptProcessor(4096, 1, 1);
            
            // 连接节点
            source.connect(this.audioProcessor);
            this.audioProcessor.connect(this.audioContext.destination);
            
            // 处理音频数据
            this.audioProcessor.onaudioprocess = async (e) => {
                if (!this.recognitionSessionId) return;
                
                const inputData = e.inputBuffer.getChannelData(0);
                // 转换为16位PCM数据
                const pcmData = this.floatTo16BitPCM(inputData);
                
                // 发送音频数据
                try {
                    await this.sendAudioData(pcmData);
                } catch (error) {
                    console.error('音频数据发送失败:', error);
                    // 如果发送失败，停止录音
                    this.stopRecording();
                }
            };
        } catch (error) {
            console.error('音频流处理初始化失败:', error);
        }
    }
    
    // 浮点数转16位PCM
    floatTo16BitPCM(input) {
        const output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return output;
    }
    
    // 发送音频数据到后端
    async sendAudioData(pcmData) {
        if (!this.recognitionSessionId) return;
        
        try {
            const response = await fetch('/api/audio/send-audio-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.recognitionSessionId,
                    audio_data: Array.from(pcmData)
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                // 不再处理中间识别结果，只返回成功状态
                return result;
            } else {
                throw new Error('网络请求失败');
            }
        } catch (error) {
            console.error('发送音频数据失败:', error);
            throw error;
        }
    }
    
    // 语音识别完成回调
    onSpeechRecognized(text) {
        console.log('识别到语音文本:', text);
        if (text.trim()) {
            // 保存识别到的文本
            this.recognizedText = text;
            
            // 发送识别到的文本给角色
            this.sendTextToCharacter(text);
        }
    }
    
    // 发送文本给角色
    async sendTextToCharacter(text) {
        if (!this.app.currentCharacter) {
            this.app.showModal('请先选择一个角色');
            // 停止录音
            this.stopRecording();
            return;
        }
        
        // 立即在聊天界面中显示用户识别到的文本
        this.app.addMessageToUI('user', text);
        
        // 显示处理状态
        const processingId = this.app.addThinkingMessage('正在处理语音...');
        
        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    character_id: this.app.currentCharacter.character_id,
                    message: text,
                    conversation_id: this.app.currentConversation?.conversation_id,
                    input_mode: this.app.inputMode // 传递输入模式
                })
            });
            
            if (response.ok) {
                this.app.removeThinkingMessage(processingId);
                
                // 创建空的AI消息容器
                const aiMessageId = this.app.createStreamingMessage();
                
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
                                    this.app.updateStreamingMessage(aiMessageId, aiContent);
                                } else if (data.type === 'end') {
                                    // 流式输出完成
                                    console.log('流式输出完成');
                                    
                                    // 如果有音频数据且在语音模式下，播放音频
                                    if (audioData && this.app.inputMode === 'voice') {
                                        await this.playAudioFromBase64(audioData);
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
                    this.app.currentConversation = this.app.currentConversation || {};
                    this.app.currentConversation.conversation_id = conversationId;
                    this.app.updateLocalConversationState(text, aiContent, conversationId);
                    
                    // 异步刷新对话列表
                    this.app.loadConversations().catch(console.error);
                }
            } else {
                this.app.removeThinkingMessage(processingId);
                this.app.addMessageToUI('assistant', '抱歉，我现在无法回复您的消息。');
            }
        } catch (error) {
            console.error('发送消息失败:', error);
            this.app.removeThinkingMessage(processingId);
            this.app.addMessageToUI('assistant', '网络连接失败，请稍后重试。');
        } finally {
            // 确保录音被停止
            this.stopRecording();
        }
    }
    
    // 播放Base64编码的音频数据
    async playAudioFromBase64(base64Audio) {
        try {
            // 将Base64数据转换为Blob
            const binary = atob(base64Audio);
            const array = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                array[i] = binary.charCodeAt(i);
            }
            
            // 创建Blob对象
            const blob = new Blob([array], { type: 'audio/pcm' });
            const url = URL.createObjectURL(blob);
            
            // 播放音频
            this.audioPlayer.src = url;
            await this.audioPlayer.play();
            
            // 清理URL对象
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('播放音频失败:', error);
        }
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
    
    showVoiceUnavailableMessage() {
        // 显示语音功能不可用的友好提示
        const message = `
            🎤 语音功能暂时不可用<br><br>
            您可以：<br>
            • 使用文字输入进行对话<br>
            • 稍后再试语音功能<br><br>
            <small>技术原因：API服务配置需要更新</small>
        `;
        
        this.app.addMessageToUI('assistant', message);
        
        // 同时显示模态框提示
        this.app.showModal('语音功能暂时不可用，请使用文字输入进行对话。');
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