// Ambil session_id dari meta tag
const sessionId = document.querySelector('meta[name="session-id"]').getAttribute('content');
const ws = new WebSocket(`ws://${window.location.host}/ws?session_id=${sessionId}`);

let allDevices = [];
let currentDeleteDeviceId = null;

// Elemen DOM
const addBtn = document.getElementById('addBtn');
const addForm = document.getElementById('addForm');
const closeForm = document.getElementById('closeForm');
const cancelForm = document.getElementById('cancelForm');
const submitAddDevice = document.getElementById('submitAddDevice');
const confirmModal = document.getElementById('confirmModal');
const confirmCancel = document.getElementById('confirmCancel');
const confirmOK = document.getElementById('confirmOK');

// Helper: Tampilkan/hide form
function showForm() {
    addForm.classList.add('form-visible');
    document.body.style.overflow = 'hidden';
}
function hideForm() {
    addForm.classList.remove('form-visible');
    document.body.style.overflow = '';
    document.getElementById('new-device-id').value = '';
    document.getElementById('new-device-name').value = '';
    document.getElementById('new-device-location').value = '';
}

// Helper: Tampilkan/hide modal hapus
function showConfirmModal(deviceId) {
    currentDeleteDeviceId = deviceId;
    confirmModal.classList.add('visible');
}
function hideConfirmModal() {
    confirmModal.classList.remove('visible');
    currentDeleteDeviceId = null;
}

// Helper: Kirim data ke backend
function sendToBackend(data) {
    ws.send(JSON.stringify(data));
}

// Event Listeners
addBtn.addEventListener('click', showForm);
closeForm.addEventListener('click', hideForm);
cancelForm.addEventListener('click', hideForm);
addForm.addEventListener('click', (e) => {
    if (e.target === addForm) hideForm();
});

submitAddDevice.addEventListener('click', addDevice);

confirmCancel.addEventListener('click', hideConfirmModal);
confirmOK.addEventListener('click', confirmDelete);
confirmModal.addEventListener('click', (e) => {
    if (e.target === confirmModal) hideConfirmModal();
});

// Validasi & Kirim Tambah Device
function addDevice() {
    const idInput = document.getElementById('new-device-id');
    const nameInput = document.getElementById('new-device-name');
    const locationInput = document.getElementById('new-device-location');

    const id = idInput.value.trim();
    const name = nameInput.value.trim();
    const location = locationInput.value.trim();

    // Reset error
    idInput.classList.remove('border-red-500');
    nameInput.classList.remove('border-red-500');
    document.getElementById('idError').classList.add('hidden');
    document.getElementById('nameError').classList.add('hidden');
    document.getElementById('formError').classList.add('hidden');

    let hasError = false;

    if (!id) {
        idInput.classList.add('border-red-500');
        document.getElementById('idError').textContent = 'Device ID is required';
        document.getElementById('idError').classList.remove('hidden');
        hasError = true;
    }

    if (!name) {
        nameInput.classList.add('border-red-500');
        document.getElementById('nameError').textContent = 'Tank Name is required';
        document.getElementById('nameError').classList.remove('hidden');
        hasError = true;
    }

    if (hasError) {
        document.getElementById('errorMessage').textContent = 'Device ID and Tank Name are required!';
        document.getElementById('formError').classList.remove('hidden');
        return;
    }

    sendToBackend({
        type: "add_device",
        device: { id, name, location }
    });
    hideForm();
}

function confirmDelete() {
    if (currentDeleteDeviceId) {
        sendToBackend({ type: "remove_device", device_id: currentDeleteDeviceId });
        hideConfirmModal();
    }
}

function sendCommand(deviceId, command, params) {
    sendToBackend({ type: "command", device_id: deviceId, command, params });
}

function renderDevices() {
    const container = document.getElementById('devices-container');
    const emptyState = document.getElementById('empty-state');

    if (allDevices.length === 0) {
        container.classList.add('hidden');
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');
    container.classList.remove('hidden');

    container.innerHTML = allDevices.map(d => `
        <div class="panel overflow-hidden">
            <div class="p-5">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h3 class="text-lg font-bold text-gray-800">${d.name}</h3>
                        <p class="text-gray-600 text-sm">${d.location || '—'}</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs px-2 py-1 rounded-full ${
                            d.mode === 'automatic'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-amber-100 text-amber-800'
                        }">
                            ${d.mode === 'automatic' ? 'Auto' : 'Manual'}
                        </span>
                        <button onclick="showConfirmModal('${d.id}')" class="text-gray-400 hover:text-red-500">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                            </svg>
                        </button>
                    </div>
                </div>

                <div class="mb-4">
                    <div class="flex justify-between text-xs text-gray-600 mb-1">
                        <span>Water Level</span>
                        <span class="font-medium text-red-700">${d.waterLevel?.toFixed(1) || 0}%</span>
                    </div>
                    <div class="water-bar">
                        <div class="water-fill" style="width: ${Math.max(5, d.waterLevel || 0)}%"></div>
                    </div>
                </div>

                <div class="flex justify-between items-center text-sm py-2 border-t border-red-100">
                    <div class="flex items-center gap-2">
                        <span class="status-dot ${
                            d.pumpStatus ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                        }"></span>
                        <span class="${d.pumpStatus ? 'text-green-700 font-medium' : 'text-gray-600'}">
                            Pump: ${d.pumpStatus ? 'ON' : 'OFF'}
                        </span>
                    </div>
                    <span class="text-xs text-gray-500">${d.id?.substring(0, 6)}...</span>
                </div>

                <div class="mt-3 flex flex-wrap gap-2">
                    <button
                        onclick="sendCommand('${d.id}', 'setMode', '${d.mode === 'automatic' ? 'manual' : 'automatic'}')"
                        class="flex-1 min-w-[100px] text-xs py-1.5 rounded-lg font-medium ${
                            d.mode === 'automatic'
                                ? 'bg-red-600 hover:bg-red-700 text-white'
                                : 'bg-gray-600 hover:bg-gray-700 text-white'
                        }">
                        Switch to ${d.mode === 'automatic' ? 'Manual' : 'Auto'}
                    </button>
                    ${d.mode === 'manual' ? `
                        <button onclick="sendCommand('${d.id}', 'setPumpStatus', true)"
                                class="text-xs py-1.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg">
                            ON
                        </button>
                        <button onclick="sendCommand('${d.id}', 'setPumpStatus', false)"
                                class="text-xs py-1.5 px-3 bg-rose-600 hover:bg-rose-700 text-white rounded-lg">
                            OFF
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

// WebSocket Events
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "all_devices") {
        allDevices = msg.data;
        renderDevices();
    }
};

ws.onopen = () => console.log("✅ Connected to AquaControl");
ws.onerror = (error) => console.error("❌ WebSocket error:", error);
ws.onclose = () => {
    console.log("⚠️ WebSocket disconnected. Reconnecting...");
    setTimeout(() => location.reload(), 3000);
};

// Pastikan fungsi global tersedia untuk inline onclick
window.showConfirmModal = showConfirmModal;
window.sendCommand = sendCommand;