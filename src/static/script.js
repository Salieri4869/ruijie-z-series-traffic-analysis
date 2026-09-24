class FirewallUI {
    constructor(baseUrl){
        this.BASE_URL = baseUrl;
        this.appData = {};
        this.isCapturing = false;

        this.inputs = {};      // 存储关键输入框
        this.clearBtns = {};   // 存储对应清除按钮

        this.initElements();
        this.bindEvents();
        this.fetchTree();
        this.setupTabs();
    }

    initElements() {
        // 获取输入框和清除按钮
        document.querySelectorAll('input').forEach(input => {
            this.inputs[input.id] = input;
        });
        document.querySelectorAll('.clear-btn').forEach(btn => {
            const targetId = btn.dataset.clearFor;
            if(targetId) this.clearBtns[targetId] = btn;
        });

        // 下拉框
        this.dropdown = document.getElementById('appDropdown');

        // 普通按钮
        this.loginBtn = document.getElementById('loginBtn');
        this.treeBtn = document.getElementById('treeBtn');
        this.sessionBtn = document.getElementById('sessionBtn');
        this.startCaptureBtn = document.getElementById('startCaptureBtn');
        this.stopCaptureBtn = document.getElementById('stopCaptureBtn');

        // 结果显示区域
        this.resultEl = document.getElementById('sessionResult');
        this.captureResult = document.getElementById('captureResult');
    }

    bindEvents() {
        // 按钮事件
        this.loginBtn.addEventListener('click', () => this.login());
        this.treeBtn.addEventListener('click', () => this.fetchTree());
        this.sessionBtn.addEventListener('click', () => this.getSessionInfo());
        this.startCaptureBtn.addEventListener('click', () => this.startCapture());
        this.stopCaptureBtn.addEventListener('click', () => this.stopCapture());

        // 清除按钮显示/点击逻辑
        Object.keys(this.clearBtns).forEach(id => {
            const inputEl = this.inputs[id];
            const btn = this.clearBtns[id];

            inputEl.addEventListener('input', () => {
                btn.style.display = inputEl.value ? 'block' : 'none';
            });

            btn.addEventListener('click', () => {
                inputEl.value = '';
                btn.style.display = 'none';
                inputEl.focus();
                if(id === 'appDesc') this.dropdown.style.display = 'none';
            });
        });

        // appDesc 下拉框点击外部隐藏
        const wrapper = this.inputs['appDesc'].parentElement; // input + clearBtn + dropdown
        document.addEventListener('click', e => {
            if (!wrapper.contains(e.target)) {
                this.dropdown.style.display = 'none';
            }
        });

        // appDesc 输入时更新下拉
        this.inputs['appDesc'].addEventListener('input', e => {
            this.updateDropdown(e.target.value);
        });
    }

    setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));

                btn.classList.add('active');
                const tabId = btn.getAttribute('data-tab');
                document.getElementById(`${tabId}-tab`).classList.add('active');
            });
        });
    }

    async login() {
        this.toggleBtn(this.loginBtn,true,'请求中...');
        try{
            const resp = await fetch(`${this.BASE_URL}/login`);
            const data = await resp.json();
            if(resp.ok) this.showToast(`登录成功: ${data.msg}`,'success');
            else throw new Error(data.msg||'请求失败');
        }catch(e){ this.showToast(`登录错误: ${e.message}`,'error'); }
        finally{ this.toggleBtn(this.loginBtn,false,'登录'); }
    }

    async fetchTree() {
        this.toggleBtn(this.treeBtn,true,'请求中...');
        try{
            const resp = await fetch(`${this.BASE_URL}/tree`);
            const data = await resp.json();
            if(resp.ok){
                this.appData = data;
                this.showToast('树结构获取成功！','success');
            } else throw new Error(data.msg||'请求失败');
        }catch(e){ this.showToast(`树结构错误: ${e.message}`,'error'); }
        finally{ this.toggleBtn(this.treeBtn,false,'刷新应用列表'); }
    }

    updateDropdown(inputVal) {
        this.dropdown.innerHTML = '';
        if(!inputVal) { this.dropdown.style.display='none'; return; }

        const keys = Object.keys(this.appData).filter(k =>
            k.toLowerCase().includes(inputVal.toLowerCase())
        );

        if(keys.length === 0){ this.dropdown.style.display='none'; return; }

        keys.forEach(k => {
            const div = document.createElement('div');
            div.textContent = k;
            div.style.padding = '5px 10px';
            div.style.cursor = 'pointer';
            div.addEventListener('click', () => {
                this.inputs['appDesc'].value = k;
                this.dropdown.style.display = 'none';
                const clearBtn = this.clearBtns['appDesc'];
                if(clearBtn) clearBtn.style.display = 'block';
            });
            div.addEventListener('mouseenter', () => div.style.backgroundColor = '#f0f0f0');
            div.addEventListener('mouseleave', () => div.style.backgroundColor = '');
            this.dropdown.appendChild(div);
        });

        this.dropdown.style.display = 'block';
    }

    async getSessionInfo() {
        const forwardSrc = this.inputs['forwardSrc'].value.trim();
        const forwardDst = this.inputs['forwardDst'].value.trim();
        const appDesc = this.inputs['appDesc'].value.trim();
        const params = new URLSearchParams();
        if(forwardSrc) params.set('forward_src', forwardSrc);
        if(forwardDst) params.set('forward_dst', forwardDst);
        if(appDesc) params.set('app_desc', appDesc);

        try{
            this.toggleBtn(this.sessionBtn,true,'请求中...');
            const resp = await fetch(`${this.BASE_URL}/get_session_info?${params}`);
            const data = await resp.json();
            if(data.msg === '登录状态已过期') {
                this.showToast('登录状态已过期，自动重新登录！', 'error');
                this.loginBtn.click();
            } else if(resp.ok) {
                this.showToast('会话信息获取成功！','success');
                this.renderTable(data);
            } else throw new Error(data.msg||'请求失败');
        }catch(e){
            this.showToast(`错误: ${e.message}`,'error');
            this.resultEl.innerHTML = `<p>获取会话信息时出现错误: ${e.message}</p>`;
        }finally{ this.toggleBtn(this.sessionBtn,false,'获取会话信息'); }
    }

    async startCapture() {
        if(this.isCapturing) return;
        this.toggleBtn(this.startCaptureBtn, true, "启动中...");
        try{
            const resp = await fetch(`${this.BASE_URL}/capture/start`, { method: "POST" });
            const data = await resp.json();
            if(!resp.ok) throw new Error(data.msg || "请求失败");

            this.showToast('抓包已开始','success');
            this.captureResult.innerHTML = `<p>${JSON.stringify(data.msg)}</p>`;
            this.isCapturing = true;
            this.updateCaptureButtons();
        }catch(e){
            this.showToast(`错误: ${e.message}`,'error');
        }finally{
            this.updateCaptureButtons();
            this.toggleBtn(this.startCaptureBtn, false, "开始抓包");
        }
    }

    async stopCapture() {
        if(!this.isCapturing) return;

        const outputFile = this.inputs['outputFile'].value;
        const captureMode = document.getElementById('captureMode').value;
        if(!outputFile){
            this.showToast("请填写输出文件名","error");
            return;
        }

        this.toggleBtn(this.stopCaptureBtn,true,"停止中...");
        try{
            const resp = await fetch(`${this.BASE_URL}/capture/stop`, {
                method:"POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ output_file: outputFile,mode:captureMode})
            });
            const data = await resp.json();
            if(!resp.ok) throw new Error(data.msg || "请求失败");

            this.showToast('抓包已停止','success');
            this.captureResult.innerHTML = `<p>${JSON.stringify(data.msg)}</p>`;
            this.isCapturing = false;
            this.updateCaptureButtons();
        }catch(e){
            this.showToast(`错误: ${e.message}`,'error');
        }finally{
            this.updateCaptureButtons();
            this.toggleBtn(this.stopCaptureBtn,false,"停止抓包");
        }
    }

    renderTable(data){
        this.resultEl.innerHTML='';
        const table = document.createElement('table');
        table.style.width='100%';
        table.style.borderCollapse='collapse';
        const keys = Array.isArray(data) && data.length ? Object.keys(data[0]) : Object.keys(data);

        const thead = document.createElement('thead');
        const tr = document.createElement('tr');
        keys.forEach(k=>{
            const th = document.createElement('th');
            th.textContent = k;
            th.style.border='1px solid #ddd';
            th.style.padding='8px';
            th.style.backgroundColor='#f2f2f2';
            th.style.textAlign='left';
            tr.appendChild(th);
        });
        thead.appendChild(tr);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        if(Array.isArray(data)){
            data.forEach(item=>{
                const row = document.createElement('tr');
                keys.forEach(k=>{
                    const td = document.createElement('td');
                    td.textContent = item[k];
                    td.style.border='1px solid #ddd';
                    td.style.padding='8px';
                    row.appendChild(td);
                });
                tbody.appendChild(row);
            });
        }else{
            const row = document.createElement('tr');
            keys.forEach(k=>{
                const td = document.createElement('td');
                td.textContent = data[k];
                td.style.border='1px solid #ddd';
                td.style.padding='8px';
                row.appendChild(td);
            });
            tbody.appendChild(row);
        }
        table.appendChild(tbody);
        this.resultEl.appendChild(table);
    }

    toggleBtn(btn,disabled,text){ btn.disabled=disabled; btn.textContent=text; }

    showToast(message,type='info'){
        const container=document.getElementById('toastContainer');
        const toast=document.createElement('div');
        toast.className=`toast ${type}`;
        const icons={success:'✅',error:'❌',info:'ℹ️'};
        toast.innerHTML=`<div class="content"><span>${icons[type]}</span><span>${message}</span></div><span class="close-btn">✖</span>`;
        const closeBtn = toast.querySelector('.close-btn');
        closeBtn.addEventListener('click',()=>{ toast.style.animation='fadeOut 0.5s forwards'; setTimeout(()=>toast.remove(),500); });
        container.appendChild(toast);
        setTimeout(()=>{ toast.style.animation='fadeOut 0.5s forwards'; setTimeout(()=>toast.remove(),500); },5000);
    }

    updateCaptureButtons(){
        if(this.isCapturing){
            this.startCaptureBtn.disabled = true;
            this.stopCaptureBtn.disabled = false;
        }else{
            this.startCaptureBtn.disabled = false;
            this.stopCaptureBtn.disabled = true;
        }
    }
}

window.addEventListener('DOMContentLoaded', ()=> {
    new FirewallUI('http://localhost:8000');
});
