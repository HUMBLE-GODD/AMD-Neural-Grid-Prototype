const API_BASE = "http://localhost:8000/api";
const WS_URL = "ws://localhost:8000/ws/frontend";

// Elements
const connStatus = document.getElementById('connection-status');
const promptInput = document.getElementById('prompt-input');
const generateBtn = document.getElementById('generate-btn');
const outputText = document.getElementById('output-text');
const nodesGrid = document.getElementById('nodes-grid');
const leaderboardTable = document.getElementById('leaderboard-table');
const ledgerHash = document.getElementById('ledger-hash');
const cryptoNonce = document.getElementById('crypto-nonce');
const cryptoPayload = document.getElementById('crypto-payload');

const routingOverlay = document.getElementById('routing-overlay');
const currentStageBadge = document.getElementById('current-stage-badge');
const currentNodeBadge = document.getElementById('current-node-badge');

const summaryOverlay = document.getElementById('summary-overlay');

let ws;
let isGenerating = false;
let failuresHandled = 0;

// Nodes data
const nodeData = {
    "Node-A": { status: "Offline", stage: 1, name: "Node A (Stage 1)" },
    "Node-B": { status: "Offline", stage: 2, name: "Node B (Stage 2)" },
    "Node-C": { status: "Offline", stage: 3, name: "Node C (Stage 3)" }
};

function initWebSocket() {
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        connStatus.innerHTML = '<i class="fa-solid fa-circle-check mr-1"></i> Connected';
        connStatus.className = "px-3 py-1 rounded-full text-sm font-medium border border-green-500 text-green-500";
        fetchMetrics();
    };
    
    ws.onclose = () => {
        connStatus.innerHTML = '<i class="fa-solid fa-circle-xmark mr-1"></i> Disconnected';
        connStatus.className = "px-3 py-1 rounded-full text-sm font-medium border border-red-500 text-red-500";
        setTimeout(initWebSocket, 3000);
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleSocketEvent(data);
    };
}

function handleSocketEvent(data) {
    if (data.event === "system_status") {
        fetchMetrics();
    } 
    else if (data.event === "node_failed") {
        updateNodeCard(data.node_id, "Failed");
        failuresHandled++;
        document.getElementById('summary-failures').innerText = failuresHandled;
        fetchMetrics();
    }
    else if (data.event === "stage_start") {
        showRouting(data.stage, data.node);
        // USP 5: Privacy Update
        cryptoNonce.innerText = data.nonce_preview;
        cryptoPayload.innerText = data.encrypted_preview;
        
        const card = document.getElementById(`card-${data.node}`);
        if (card) {
            card.classList.add('anim-processing', 'stage-active');
            
            // Reassignment UI indication
            if (nodeData[data.node] && nodeData[data.node].flashGreen) {
                nodeData[data.node].flashGreen = false;
                card.classList.add('bg-green-900/80', 'border-green-400');
                setTimeout(() => card.classList.remove('bg-green-900/80', 'border-green-400'), 1000);
            }
        }
    }
    else if (data.event === "stage_complete") {
        document.getElementById(`card-${data.node}`)?.classList.remove('anim-processing', 'stage-active');
        
        if (data.stage === 3 && data.token_text) {
            outputText.innerText += data.token_text;
            // Scroll to bottom
            outputText.parentElement.scrollTop = outputText.parentElement.scrollHeight;
        }
        fetchMetrics(); // Update rewards
    }
    else if (data.event === "reroute_start") {
        console.warn(`Rerouting stage ${data.stage} after node failure (USP 3)`);
        showTemporaryOverlay('✓ Stage Successfully Reassigned', false);
        
        // Let the next assigned node flash green
        Object.keys(nodeData).forEach(id => nodeData[id].flashGreen = true);
    }
    else if (data.event === "session_complete") {
        isGenerating = false;
        generateBtn.disabled = false;
        generateBtn.innerText = "Generate (20 Tokens)";
        
        ledgerHash.innerText = data.ledger_hash;
        
        routingOverlay.style.opacity = "0";
        
        // Populate summary
        document.querySelector('.content-tokens').innerText = `${data.summary.total_tokens} Tokens`;
        // Each token is 3 stages, 20 tokens = 60 stages
        document.querySelector('.content-stages').innerText = `${data.summary.total_tokens * 3} Transitions`;
        
        // Show overlay
        setTimeout(() => {
            summaryOverlay.classList.remove('hidden');
        }, 1000);
    }
}

function showRouting(stage, node) {
    currentStageBadge.innerText = stage;
    currentNodeBadge.innerText = node;
    routingOverlay.style.opacity = "1";
}

function renderNodes() {
    nodesGrid.innerHTML = "";
    Object.keys(nodeData).forEach(id => {
        const info = nodeData[id];
        const color = info.status === "Active" ? "green" : (info.status === "Offline" ? "slate" : "red");
        
        // Stage badges to show separation of concerns (USP 1)
        let badges = "";
        if (info.stage === 1) badges = `<span class="bg-blue-900 text-blue-300 text-[10px] px-2 py-0.5 rounded ml-2">Embed + L0-1</span>`;
        if (info.stage === 2) badges = `<span class="bg-purple-900 text-purple-300 text-[10px] px-2 py-0.5 rounded ml-2">Layers 2-3</span>`;
        if (info.stage === 3) badges = `<span class="bg-indigo-900 text-indigo-300 text-[10px] px-2 py-0.5 rounded ml-2">Layers 4-5 + Head</span>`;

        html = `
            <div id="card-${id}" class="node-card bg-slate-900 border border-slate-700 rounded-lg p-4 flex flex-col justify-between h-32">
                <div class="flex justify-between items-start">
                    <h3 class="font-bold text-slate-200">${id} ${badges}</h3>
                    <div class="w-2 h-2 rounded-full bg-${color}-500 ${info.status==='Active' ? 'animate-pulse' : ''}"></div>
                </div>
                <div class="text-sm mt-2 text-${color}-400 font-medium ${info.status==='Failed' ? 'animate-pulse font-bold' : ''}">
                    <i class="fa-solid fa-${info.status==='Active'?'server':(info.status==='Offline'?'power-off':'skull')} mr-1"></i> ${info.status==='Failed' ? 'FAILED' : info.status}
                </div>
                <div class="text-xs text-slate-500 mt-2">Local CPU Instance</div>
            </div>
        `;
        nodesGrid.innerHTML += html;
    });
}

function updateNodeCard(id, status) {
    if (nodeData[id]) {
        nodeData[id].status = status;
        renderNodes();
    }
}

function showTemporaryOverlay(msg, isError) {
    const el = document.createElement('div');
    el.className = `fixed top-10 left-1/2 transform -translate-x-1/2 p-4 rounded-lg font-bold text-white shadow-2xl transition-opacity duration-500 z-50 flex items-center gap-2 ${isError ? 'bg-red-600/90 border border-red-500' : 'bg-green-600/90 border border-green-500'}`;
    el.innerHTML = isError ? `<i class="fa-solid fa-triangle-exclamation"></i> ${msg}` : `<i class="fa-solid fa-check"></i> ${msg}`;
    document.body.appendChild(el);
    setTimeout(() => { 
        el.style.opacity = '0'; 
        setTimeout(() => el.remove(), 500); 
    }, 2500);
}

async function fetchMetrics() {
    try {
        const res = await fetch(`${API_BASE}/metrics`);
        const data = await res.json();
        
        leaderboardTable.innerHTML = "";
        
        // Preset default modes to offline so they render even if API returns nothing yet
        Object.keys(nodeData).forEach(id => nodeData[id].status = "Offline");
        
        // Sort by balance descending
        data.nodes.sort((a,b) => b.balance - a.balance);
        
        data.nodes.forEach(n => {
            // Update node status
            if (nodeData[n.node_id]) {
                nodeData[n.node_id].status = n.status;
            } else {
                // If a new node appeared
                nodeData[n.node_id] = { status: n.status, stage: 1 };
            }
            
            // Render row
            const tr = document.createElement('tr');
            tr.className = "border-b border-slate-700/50 last:border-0";
            tr.innerHTML = `
                <td class="py-2"><span class="font-mono text-slate-300">${n.node_id}</span></td>
                <td class="py-2">${n.compute_time.toFixed(2)}s</td>
                <td class="py-2 text-right font-mono text-yellow-400 font-bold">${n.balance.toFixed(4)}</td>
            `;
            leaderboardTable.appendChild(tr);
        });
        
        if (data.ledger_hash && data.ledger_hash !== "None") {
            ledgerHash.innerText = data.ledger_hash;
        }
        
        renderNodes();
        
    } catch (e) {
        console.error("Failed to fetch metrics", e);
    }
}

// Events
generateBtn.addEventListener('click', async () => {
    if (isGenerating) return;
    
    const prompt = promptInput.value.trim();
    if (!prompt) return;
    
    isGenerating = true;
    generateBtn.disabled = true;
    generateBtn.innerText = "Generating...";
    outputText.innerText = prompt; // Start with the prompt
    
    failuresHandled = 0;
    Object.keys(nodeData).forEach(id => nodeData[id].isKilled = false);
    
    try {
        await fetch(`${API_BASE}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt })
        });
    } catch (e) {
        console.error("Failed to start generation", e);
        isGenerating = false;
        generateBtn.disabled = false;
        generateBtn.innerText = "Generate (20 Tokens)";
    }
});

const demoKillBtn = document.getElementById('demo-kill-btn');
if (demoKillBtn) {
    demoKillBtn.addEventListener('click', async () => {
        if (!isGenerating) return;
        try {
            const res = await fetch(`${API_BASE}/kill-node`, { method: 'POST' });
            const data = await res.json();
            
            if (data.status === "success") {
                const nodeId = data.killed_node;
                
                // Overlay message
                showTemporaryOverlay(`Node ${nodeId} Failed — Reassigning Stage...`, true);
                
                // Append system output
                outputText.innerText += `\n[System] Stage Reassigned from ${nodeId}\n`;
                outputText.parentElement.scrollTop = outputText.parentElement.scrollHeight;
                
                // Force an immediate visual blink without waiting for websocket
                const card = document.getElementById(`card-${nodeId}`);
                if (card) {
                    card.classList.remove('border-slate-700', 'anim-processing', 'stage-active');
                    card.classList.add('border-red-500', 'animate-pulse', 'bg-red-900/20');
                }
            }
        } catch(e) {
            console.error(e);
        }
    });
}

// Setup
renderNodes();
initWebSocket();
