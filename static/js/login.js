class LoginManager {
    constructor() {
        this.form = document.getElementById('login-form');
        this.usernameInput = document.getElementById('username');
        this.errorMessage = document.getElementById('error-message');
        this.loginBtn = null;
        
        this.init();
    }
    
    init() {
        // 检查是否已登录
        this.checkExistingSession();
        
        // 绑定事件
        this.bindEvents();
        
        // 设置焦点
        this.usernameInput.focus();
    }
    
    bindEvents() {
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
        
        // 输入时隐藏错误信息
        this.usernameInput.addEventListener('input', () => {
            this.hideError();
        });
        
        // 回车键登录
        this.usernameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleLogin();
            }
        });
    }
    
    async checkExistingSession() {
        try {
            const response = await fetch('/api/user/info');
            if (response.ok) {
                // 已登录，跳转到主页
                window.location.href = '/';
            }
        } catch (error) {
            // 未登录或出错，继续显示登录页面
            console.log('未登录，显示登录页面');
        }
    }
    
    async handleLogin() {
        const username = this.usernameInput.value.trim();
        
        if (!username) {
            this.showError('请输入用户名');
            return;
        }
        
        if (username.length < 2) {
            this.showError('用户名至少需要2个字符');
            return;
        }
        
        if (username.length > 20) {
            this.showError('用户名不能超过20个字符');
            return;
        }
        
        // 验证用户名格式（只允许字母、数字、中文和下划线）
        if (!/^[a-zA-Z0-9\u4e00-\u9fa5_]+$/.test(username)) {
            this.showError('用户名只能包含字母、数字、中文和下划线');
            return;
        }
        
        await this.login(username);
    }
    
    async login(username) {
        this.setLoading(true);
        this.hideError();
        
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 登录成功
                this.showSuccess('登录成功，正在跳转...');
                
                // 延迟跳转以显示成功信息
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                this.showError(result.error || '登录失败');
            }
            
        } catch (error) {
            console.error('登录请求失败:', error);
            this.showError('网络连接失败，请检查网络后重试');
        } finally {
            this.setLoading(false);
        }
    }
    
    setLoading(loading) {
        if (!this.loginBtn) {
            this.loginBtn = this.form.querySelector('button[type="submit"]');
        }
        
        if (loading) {
            this.loginBtn.disabled = true;
            this.loginBtn.classList.add('loading');
            this.loginBtn.textContent = '登录中...';
        } else {
            this.loginBtn.disabled = false;
            this.loginBtn.classList.remove('loading');
            this.loginBtn.textContent = '登录';
        }
    }
    
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
        this.errorMessage.style.background = 'linear-gradient(45deg, #ff4757, #ff6b7a)';
        
        // 震动效果
        this.errorMessage.style.animation = 'none';
        setTimeout(() => {
            this.errorMessage.style.animation = 'shake 0.5s ease-in-out';
        }, 10);
        
        // 3秒后自动隐藏
        setTimeout(() => {
            this.hideError();
        }, 3000);
    }
    
    showSuccess(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
        this.errorMessage.style.background = 'linear-gradient(45deg, #5cb85c, #4cae4c)';
        this.errorMessage.style.animation = 'none';
    }
    
    hideError() {
        this.errorMessage.style.display = 'none';
    }
}

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new LoginManager();
});

// 处理页面可见性变化
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        // 页面重新可见时，检查登录状态
        const usernameInput = document.getElementById('username');
        if (usernameInput && document.activeElement !== usernameInput) {
            usernameInput.focus();
        }
    }
});