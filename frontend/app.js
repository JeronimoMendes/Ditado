const fileInput = document.getElementById("file-input");
const fileName = document.getElementById("file-name");
const uploadBtn = document.getElementById("upload-btn");
const dropZone = document.getElementById("drop-zone");
const uploadSection = document.getElementById("upload-section");
const statusSection = document.getElementById("status-section");
const statusText = document.getElementById("status-text");
const errorSection = document.getElementById("error-section");
const errorText = document.getElementById("error-text");
const resultSection = document.getElementById("result-section");
const transcript = document.getElementById("transcript");
const downloadBtn = document.getElementById("download-btn");

let selectedFile = null;

fileInput.addEventListener("change", () => {
    selectedFile = fileInput.files[0] || null;
    fileName.textContent = selectedFile ? selectedFile.name : "";
    uploadBtn.disabled = !selectedFile;
});

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("audio/")) {
        selectedFile = file;
        fileInput.files = e.dataTransfer.files;
        fileName.textContent = file.name;
        uploadBtn.disabled = false;
    }
});

uploadBtn.addEventListener("click", uploadFile);
downloadBtn.addEventListener("click", () => {
    if (downloadBtn.dataset.jobId) {
        window.location.href = `/api/result/${downloadBtn.dataset.jobId}/download`;
    }
});

async function uploadFile() {
    if (!selectedFile) return;

    uploadSection.hidden = true;
    statusSection.hidden = false;
    errorSection.hidden = true;
    resultSection.hidden = true;
    statusText.textContent = "A enviar ficheiro...";

    const form = new FormData();
    form.append("file", selectedFile);

    try {
        const res = await fetch("/api/transcribe", { method: "POST", body: form });
        if (!res.ok) throw new Error("Erro ao enviar ficheiro");
        const { job_id } = await res.json();
        statusText.textContent = "A processar transcrição...";
        pollStatus(job_id);
    } catch (err) {
        showError(err.message);
    }
}

function pollStatus(jobId) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`/api/status/${jobId}`);
            const data = await res.json();

            if (data.status === "done") {
                clearInterval(interval);
                await fetchResult(jobId);
            } else if (data.status === "error") {
                clearInterval(interval);
                showError(data.error || "Erro na transcrição");
            }
        } catch {
            clearInterval(interval);
            showError("Erro de conexão com o servidor");
        }
    }, 2000);
}

async function fetchResult(jobId) {
    const res = await fetch(`/api/result/${jobId}`);
    const data = await res.json();

    statusSection.hidden = true;
    resultSection.hidden = false;
    downloadBtn.dataset.jobId = jobId;

    renderTranscript(data.utterances);
}

function renderTranscript(utterances) {
    transcript.innerHTML = "";
    for (const u of utterances) {
        const div = document.createElement("div");
        div.className = "utterance";
        div.innerHTML = `
            <div class="utterance-header">
                <span class="speaker-label speaker-${u.speaker % 6}">Speaker ${u.speaker + 1}</span>
                <span class="timestamp">${formatTime(u.start)}</span>
            </div>
            <p class="utterance-text">${escapeHtml(u.text)}</p>
        `;
        transcript.appendChild(div);
    }
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const h = Math.floor(m / 60);
    const mm = m % 60;
    if (h) return `${pad(h)}:${pad(mm)}:${pad(s)}`;
    return `${pad(mm)}:${pad(s)}`;
}

function pad(n) {
    return String(n).padStart(2, "0");
}

function escapeHtml(text) {
    const el = document.createElement("span");
    el.textContent = text;
    return el.innerHTML;
}

function showError(message) {
    statusSection.hidden = true;
    errorSection.hidden = false;
    uploadSection.hidden = false;
    errorText.textContent = message;
    uploadBtn.disabled = false;
}
