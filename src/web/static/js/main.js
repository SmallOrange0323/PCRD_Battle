document.addEventListener('DOMContentLoaded', () => {
    const btnScanAdb = document.getElementById('btn-scan-adb');
    const instanceMatrix = document.getElementById('instance-matrix');
    const deviceCountBadge = document.getElementById('device-count-badge');
    
    const btnParseTimeline = document.getElementById('btn-parse-timeline');
    const timelineTextInput = document.getElementById('timeline-text-input');
    const timelineVisualList = document.getElementById('timeline-visual-list');
    const stepCountBadge = document.getElementById('step-count-badge');
    const editorPartyGrid = document.getElementById('editor-party-grid');

    const inputPresetName = document.getElementById('input-preset-name');
    const btnSavePreset = document.getElementById('btn-save-preset');

    let savedPresets = [];
    let detectedCharacters = ['真步', '阿剌克涅', '涅妃', '埃拉', '水堇'];

    // 1. 探測 BS4 模擬器實例
    async function scanDevices() {
        deviceCountBadge.textContent = '廣域探測中...';
        try {
            const res = await fetch('/api/scan_devices');
            const data = await res.json();
            if (data.success) {
                renderInstanceMatrix(data.devices);
            }
        } catch (err) {
            deviceCountBadge.textContent = '探測異常';
        }
    }

    // 渲染多開模擬器卡片 (純淨選擇軸檔版)
    function renderInstanceMatrix(devices) {
        instanceMatrix.innerHTML = '';
        let connectedCount = 0;

        devices.forEach((dev, idx) => {
            if (dev.connected) connectedCount++;

            const card = document.createElement('div');
            card.className = `instance-card ${dev.connected ? 'running' : ''}`;
            card.setAttribute('data-port', dev.port);

            let optionsHtml = '<option value="current">當前編輯器中的 SET 軸</option>';
            savedPresets.forEach(p => {
                optionsHtml += `<option value="${p.name}">軸庫: ${p.name}</option>`;
            });

            card.innerHTML = `
                <div class="card-header">
                    <div class="card-title">🌸 ${dev.name}</div>
                    <div class="card-port">127.0.0.1:${dev.port}</div>
                </div>

                <div class="form-group" style="margin-top: 4px;">
                    <label style="font-size: 11px; font-weight: 700; color: #64748b; margin-bottom: 4px; display: block;">
                        選擇要執行的軸檔劇本：
                    </label>
                    <select class="form-select script-select">
                        ${optionsHtml}
                    </select>
                </div>

                <div style="display: flex; gap: 6px; margin-top: 6px;">
                    <button class="btn btn-pcrd-pink btn-start-single" style="flex: 1;" ${!dev.connected ? 'disabled' : ''}>
                        ▶️ 啟動本刀
                    </button>
                    <button class="btn btn-secondary btn-stop-single" style="width: 70px;" ${!dev.connected ? 'disabled' : ''}>
                        ⏹️ 暫停
                    </button>
                </div>
            `;

            instanceMatrix.appendChild(card);

            const btnStartSingle = card.querySelector('.btn-start-single');
            btnStartSingle.addEventListener('click', () => startSingleTask(dev.port, btnStartSingle, card.querySelector('.script-select')));
        });

        deviceCountBadge.textContent = `在線: ${connectedCount} / 共 ${devices.length} 台`;
    }

    // 2. 即時 Parse 軸並渲染【左側站位校正區】
    async function parseTimeline() {
        const text = timelineTextInput.value;
        if (!text.trim()) return;

        try {
            const res = await fetch('/api/parse_timeline', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const data = await res.json();

            if (data.success) {
                if (data.detected_characters && data.detected_characters.length > 0) {
                    detectedCharacters = data.detected_characters;
                }
                renderPartyMappingGrid();
                renderTimelineVisual(data.steps);
                stepCountBadge.textContent = `${data.total_steps} 個步驟`;
            } else {
                alert("軸解析失敗: " + data.error);
            }
        } catch (err) {
            console.error(err);
        }
    }

    // 渲染左側手動校正 P1 ~ P5 站位區
    function renderPartyMappingGrid() {
        editorPartyGrid.innerHTML = '';
        for (let pIdx = 0; pIdx < 5; pIdx++) {
            const defaultName = detectedCharacters[pIdx] || `角色${pIdx+1}`;
            let optionsHtml = detectedCharacters.map(c => `
                <option value="${c}" ${c === defaultName ? 'selected' : ''}>${c}</option>
            `).join('');

            const slotEl = document.createElement('div');
            slotEl.className = 'party-slot-item';
            slotEl.innerHTML = `
                <span class="slot-label">P${pIdx+1}</span>
                <select class="form-select slot-select" data-slot="${pIdx}">
                    ${optionsHtml}
                </select>
            `;
            editorPartyGrid.appendChild(slotEl);
        }
    }

    // 3. 儲存軸檔至預設庫
    async function savePreset() {
        const name = inputPresetName.value.trim();
        if (!name) {
            alert("請先輸入軸檔儲存名稱！");
            return;
        }

        const text = timelineTextInput.value;
        const mappingSelects = editorPartyGrid.querySelectorAll('.slot-select');
        const partyMapping = Array.from(mappingSelects).map(s => s.value);

        try {
            const res = await fetch('/api/save_preset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, text, party_mapping: partyMapping })
            });
            const data = await res.json();

            if (data.success) {
                alert(data.message);
                loadPresets();
            } else {
                alert("儲存失敗: " + data.error);
            }
        } catch (err) {
            console.error(err);
        }
    }

    // 載入所有預設軸檔
    async function loadPresets() {
        try {
            const res = await fetch('/api/get_presets');
            const data = await res.json();
            if (data.success) {
                savedPresets = data.presets;
                scanDevices(); // 重新渲染卡片選單
            }
        } catch (err) {
            console.error(err);
        }
    }

    function renderTimelineVisual(steps) {
        timelineVisualList.innerHTML = '';
        if (!steps || steps.length === 0) {
            timelineVisualList.innerHTML = '<div class="empty-state">無有效步驟</div>';
            return;
        }

        steps.forEach(step => {
            const card = document.createElement('div');
            card.className = 'step-card';
            const setTagsHtml = step.target_set.map((is_on, idx) => `
                <div class="set-tag ${is_on ? 'on' : 'off'}">P${idx+1}</div>
            `).join('');

            card.innerHTML = `
                <div style="font-weight: 700; color: #ff6b9d; font-size: 14px; width: 50px;">${step.time_str}</div>
                <div style="font-weight: 600; color: #1e293b; flex: 1;">${step.trigger_character}</div>
                <div style="display: flex; gap: 4px;">${setTagsHtml}</div>
            `;
            timelineVisualList.appendChild(card);
        });
    }

    async function startSingleTask(port, buttonEl, selectEl) {
        let text = timelineTextInput.value;
        const selectedPresetName = selectEl.value;

        if (selectedPresetName !== 'current') {
            const found = savedPresets.find(p => p.name === selectedPresetName);
            if (found) {
                text = found.raw_text;
            }
        }

        buttonEl.disabled = true;
        buttonEl.textContent = '⏳ 啟動中...';

        try {
            const res = await fetch('/api/start_task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ port, timeline_text: text })
            });
            const data = await res.json();
            if (data.success) {
                alert(`[BS4 127.0.0.1:${port}] ${data.message}`);
                buttonEl.textContent = '🟢 執行中';
            } else {
                buttonEl.disabled = false;
                buttonEl.textContent = '▶️ 啟動本刀';
            }
        } catch (err) {
            buttonEl.disabled = false;
            buttonEl.textContent = '▶️ 啟動本刀';
        }
    }

    btnScanAdb.addEventListener('click', scanDevices);
    btnParseTimeline.addEventListener('click', parseTimeline);
    btnSavePreset.addEventListener('click', savePreset);

    renderPartyMappingGrid();
    loadPresets();
    parseTimeline();
});
