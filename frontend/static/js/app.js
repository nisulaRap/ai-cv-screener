/**
 * AI CV Screener - Frontend Application
 * Main JavaScript file for handling UI interactions and API calls
 */

// ═══════════════════════════════════════════
// State Management
// ═══════════════════════════════════════════

const AppState = {
    currentRunId: null,
    uploadedFiles: [],
    pipelineRunning: false,
    lastResults: null,
    runs: [],
};

// ═══════════════════════════════════════════
// API Service
// ═══════════════════════════════════════════

const API = {
    baseURL: '/api',

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Request failed');
            }

            return data;
        } catch (error) {
            showToast('error', error.message);
            throw error;
        }
    },

    // Health check
    healthCheck() {
        return this.request('/health');
    },

    // File uploads
    uploadCV(file) {
        const formData = new FormData();
        formData.append('file', file);
        return fetch(`${this.baseURL}/upload-cv`, {
            method: 'POST',
            body: formData,
        }).then(res => res.json());
    },

    uploadCVsBatch(files) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        return fetch(`${this.baseURL}/upload-cvs/batch`, {
            method: 'POST',
            body: formData,
        }).then(res => res.json());
    },

    clearUploads() {
        return this.request('/clear-uploads', { method: 'DELETE' });
    },

    // Job description
    saveJobDescription(jobData) {
        return this.request('/job-description', {
            method: 'POST',
            body: JSON.stringify(jobData),
        });
    },

    getJobDescription(jobId) {
        return this.request(`/job-description/${jobId}`);
    },

    // Pipeline
    runPipeline(jobId = null) {
        const params = new URLSearchParams();
        if (jobId) params.append('job_id', jobId);
        return this.request(`/run-pipeline?${params.toString()}`, {
            method: 'POST',
        });
    },

    getRunStatus(runId) {
        return this.request(`/run-status/${runId}`);
    },

    getRuns() {
        return this.request('/runs');
    },

    getCandidates(runId) {
        return this.request(`/candidates/${runId}`);
    },

    getReport(runId) {
        return `${this.baseURL}/report/${runId}`;
    },
};

// ═══════════════════════════════════════════
// UI Helpers
// ═══════════════════════════════════════════

function showToast(type, message) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️',
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'toastSlideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function navigateToPage(pageId) {
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === pageId);
    });

    // Update pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.toggle('active', page.id === `page-${pageId}`);
    });

    // Update header title
    const titles = {
        dashboard: 'Dashboard',
        upload: 'Upload CVs',
        'job-description': 'Job Description',
        results: 'Results',
        history: 'Pipeline History',
    };
    document.querySelector('.page-title').textContent = titles[pageId] || 'Dashboard';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

// Helper function to animate counter values
function animateCounter(elementId, targetValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const currentValue = parseInt(element.textContent) || 0;
    
    if (currentValue === targetValue) {
        element.textContent = targetValue;
        return;
    }
    
    const diff = targetValue - currentValue;
    const steps = 20;
    const stepValue = diff / steps;
    let step = 0;
    
    const animate = () => {
        step++;
        if (step >= steps) {
            element.textContent = targetValue;
        } else {
            element.textContent = Math.round(currentValue + stepValue * step);
            requestAnimationFrame(animate);
        }
    };
    
    requestAnimationFrame(animate);
}

// ═══════════════════════════════════════════
// Dashboard Functions
// ═══════════════════════════════════════════

async function updateDashboard() {
    try {
        // First, get all runs to find the latest completed one
        const runsData = await API.getRuns();
        AppState.runs = runsData.runs || [];
        
        // Find the latest completed run
        const completedRuns = AppState.runs.filter(run => run.status === 'completed');
        
        if (completedRuns.length > 0) {
            const latestRun = completedRuns[0]; // Most recent first
            
            // If we don't have results loaded, or the run ID changed, fetch them
            if (!AppState.lastResults || AppState.lastResults.run_id !== latestRun.run_id) {
                try {
                    const results = await API.getCandidates(latestRun.run_id);
                    results.run_id = latestRun.run_id; // Store run_id for comparison
                    AppState.lastResults = results;
                } catch (error) {
                    console.error('Failed to load latest results:', error);
                }
            }
            
            // Update stats from lastResults
            if (AppState.lastResults) {
                const results = AppState.lastResults;
                animateCounter('totalCVs', results.total || 0);
                animateCounter('shortlistedCount', results.shortlisted || 0);
                animateCounter('rejectedCount', results.rejected || 0);
                
                // Calculate and display average score
                if (results.ranked_candidates && results.ranked_candidates.length > 0) {
                    const avg = results.ranked_candidates.reduce((sum, c) => sum + (c.score || 0), 0) / results.ranked_candidates.length;
                    animateCounter('avgScore', Math.round(avg));
                } else {
                    animateCounter('avgScore', 0);
                }
            }
        } else {
            // No completed runs, reset stats to 0
            animateCounter('totalCVs', 0);
            animateCounter('shortlistedCount', 0);
            animateCounter('rejectedCount', 0);
            animateCounter('avgScore', 0);
        }

        // Update recent runs table
        updateRecentRunsTable(AppState.runs);

    } catch (error) {
        console.error('Failed to update dashboard:', error);
    }
}

function updateRecentRunsTable(runs) {
    const tbody = document.getElementById('recentRunsTable');
    
    if (runs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No pipeline runs yet</td></tr>';
        return;
    }

    tbody.innerHTML = runs.slice(0, 5).map(run => `
        <tr>
            <td><code>${run.run_id}</code></td>
            <td><span class="status-badge ${run.status}">${run.status}</span></td>
            <td>${run.progress || 'N/A'}</td>
            <td>${formatDate(run.started_at)}</td>
            <td>
                ${run.status === 'completed' ? `
                    <button class="btn btn-sm btn-secondary" onclick="viewRunResults('${run.run_id}')">
                        View
                    </button>
                ` : ''}
            </td>
        </tr>
    `).join('');
}

async function loadJobInfo() {
    const container = document.getElementById('currentJobInfo');
    
    try {
        // Try to load default job description
        const jobData = await API.getJobDescription('default');
        
        container.innerHTML = `
            <div class="job-info-list">
                <div class="job-info-row">
                    <span class="job-info-label">Job Title</span>
                    <span class="job-info-separator">:</span>
                    <span class="job-info-value">${jobData.title}</span>
                </div>
                <div class="job-info-row">
                    <span class="job-info-label">Job ID</span>
                    <span class="job-info-separator">:</span>
                    <span class="job-info-value">${jobData.job_id}</span>
                </div>
                <div class="job-info-row">
                    <span class="job-info-label">Required Skills</span>
                    <span class="job-info-separator">:</span>
                    <span class="job-info-value">${jobData.required_skills.join(', ')}</span>
                </div>
                <div class="job-info-row">
                    <span class="job-info-label">Preferred Skills</span>
                    <span class="job-info-separator">:</span>
                    <span class="job-info-value">${jobData.preferred_skills && jobData.preferred_skills.length > 0 ? jobData.preferred_skills.join(', ') : 'None'}</span>
                </div>
                <div class="job-info-row">
                    <span class="job-info-label">Min Experience</span>
                    <span class="job-info-separator">:</span>
                    <span class="job-info-value">${jobData.min_experience_years} years</span>
                </div>
                <div class="job-info-row">
                    <span class="job-info-label">Education</span>
                    <span class="job-info-separator">:</span>
                    <span class="job-info-value">${jobData.education_requirement}</span>
                </div>
                <div class="job-info-row job-info-description">
                    <span class="job-info-label">Job Description</span>
                    <span class="job-info-separator">:</span>
                    <span class="job-info-value">${jobData.description}</span>
                </div>
            </div>
        `;
    } catch (error) {
        container.innerHTML = `
            <div class="no-job-info">
                <p>No job description configured.</p>
                <button class="btn btn-sm btn-primary" onclick="navigateToPage('job-description')">
                    Configure Job Description
                </button>
            </div>
        `;
    }
}

// ═══════════════════════════════════════════
// File Upload Functions
// ═══════════════════════════════════════════

function initDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    // Click to browse
    dropZone.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
        fileInput.value = ''; // Reset
    });

    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
}

function handleFiles(files) {
    const allowedTypes = ['.pdf', '.docx', '.txt'];
    const validFiles = Array.from(files).filter(file => {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        return allowedTypes.includes(ext);
    });

    if (validFiles.length === 0) {
        showToast('error', 'No valid files selected. Please upload PDF, DOCX, or TXT files.');
        return;
    }

    validFiles.forEach(file => {
        AppState.uploadedFiles.push({
            id: Date.now() + Math.random(),
            file: file,
            name: file.name,
            size: file.size,
        });
    });

    updateUploadedFilesList();
    showToast('success', `${validFiles.length} file(s) added`);
}

function updateUploadedFilesList() {
    const container = document.getElementById('uploadedFiles');

    if (AppState.uploadedFiles.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = AppState.uploadedFiles.map(item => `
        <div class="file-item" data-id="${item.id}">
            <div class="file-name">
                <span>📄</span>
                <span>${item.name}</span>
                <span class="file-size">${formatFileSize(item.size)}</span>
            </div>
            <button class="file-remove" onclick="removeFile(${item.id})">×</button>
        </div>
    `).join('');
}

function removeFile(id) {
    AppState.uploadedFiles = AppState.uploadedFiles.filter(f => f.id !== id);
    updateUploadedFilesList();
}

async function uploadFiles() {
    if (AppState.uploadedFiles.length === 0) {
        showToast('warning', 'No files to upload');
        return;
    }

    const files = AppState.uploadedFiles.map(item => item.file);
    
    try {
        const result = await API.uploadCVsBatch(files);
        showToast('success', `Successfully uploaded ${result.uploaded} file(s)`);
        AppState.uploadedFiles = [];
        updateUploadedFilesList();
    } catch (error) {
        showToast('error', 'Failed to upload files');
    }
}

async function clearUploads() {
    if (AppState.uploadedFiles.length === 0) return;

    try {
        await API.clearUploads();
        AppState.uploadedFiles = [];
        updateUploadedFilesList();
        showToast('success', 'All uploads cleared');
    } catch (error) {
        showToast('error', 'Failed to clear uploads');
    }
}

// ═══════════════════════════════════════════
// Job Description Functions
// ═══════════════════════════════════════════

function loadDefaultJob() {
    const defaultJob = {
        title: 'Senior Python Developer',
        jobId: '',
        minExperience: 3,
        educationReq: "Bachelor's degree in Computer Science or related field",
        requiredSkills: 'Python, REST APIs, SQL, Git',
        preferredSkills: 'FastAPI, Docker, PostgreSQL, Redis',
        description: 'We are looking for a Senior Python Developer to join our backend team. You will design and build scalable REST APIs, work with SQL databases, and collaborate with frontend teams. Experience with FastAPI and Docker is a strong advantage. You must be comfortable working in an agile environment.',
    };

    document.getElementById('jobTitle').value = defaultJob.title;
    document.getElementById('jobId').value = defaultJob.jobId;
    document.getElementById('minExperience').value = defaultJob.minExperience;
    document.getElementById('educationReq').value = defaultJob.educationReq;
    document.getElementById('requiredSkills').value = defaultJob.requiredSkills;
    document.getElementById('preferredSkills').value = defaultJob.preferredSkills;
    document.getElementById('jobDescription').value = defaultJob.description;

    showToast('success', 'Default job description loaded');
}

async function saveJobDescription(e) {
    e.preventDefault();

    const jobData = {
        job_id: document.getElementById('jobId').value || undefined,
        title: document.getElementById('jobTitle').value,
        required_skills: document.getElementById('requiredSkills').value
            .split(',')
            .map(s => s.trim())
            .filter(s => s),
        preferred_skills: document.getElementById('preferredSkills').value
            .split(',')
            .map(s => s.trim())
            .filter(s => s),
        min_experience_years: parseFloat(document.getElementById('minExperience').value),
        education_requirement: document.getElementById('educationReq').value,
        description: document.getElementById('jobDescription').value,
    };

    try {
        const result = await API.saveJobDescription(jobData);
        showToast('success', 'Job description saved successfully');
        
        // Update job info on dashboard
        loadJobInfo();
    } catch (error) {
        showToast('error', 'Failed to save job description');
    }
}

// ═══════════════════════════════════════════
// Pipeline Functions
// ═══════════════════════════════════════════

async function runPipeline() {
    if (AppState.pipelineRunning) {
        showToast('warning', 'Pipeline is already running');
        return;
    }

    if (AppState.uploadedFiles.length === 0) {
        showToast('warning', 'Please upload CV files first');
        navigateToPage('upload');
        return;
    }

    // Upload files first
    try {
        await uploadFiles();
    } catch (error) {
        showToast('error', 'Failed to upload files. Cannot start pipeline.');
        return;
    }

    AppState.pipelineRunning = true;
    document.getElementById('runPipelineBtn').disabled = true;

    try {
        const result = await API.runPipeline();
        AppState.currentRunId = result.run_id;
        
        // Show progress modal
        showPipelineModal();
        
        // Start polling for status
        pollPipelineStatus(result.run_id);
    } catch (error) {
        AppState.pipelineRunning = false;
        document.getElementById('runPipelineBtn').disabled = false;
        showToast('error', 'Failed to start pipeline');
    }
}

function showPipelineModal() {
    const modal = document.getElementById('pipelineModal');
    modal.classList.add('active');
    
    // Reset progress indicators
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`step${i}`).classList.remove('active', 'completed');
    }
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressStatus').textContent = 'Initializing pipeline...';
}

function closePipelineModal() {
    const modal = document.getElementById('pipelineModal');
    modal.classList.remove('active');
    
    if (AppState.pipelineRunning) {
        // If still running, user is just closing modal temporarily
        return;
    }
    
    // Navigate to results if completed
    if (AppState.currentRunId) {
        viewRunResults(AppState.currentRunId);
    }
}

async function pollPipelineStatus(runId) {
    const maxAttempts = 60; // 5 minutes max (5s interval)
    let attempts = 0;

    const poll = async () => {
        try {
            const status = await API.getRunStatus(runId);
            updatePipelineProgress(status);

            if (status.status === 'completed') {
                AppState.pipelineRunning = false;
                document.getElementById('runPipelineBtn').disabled = false;
                
                // Load results
                const results = await API.getCandidates(runId);
                results.run_id = runId; // Store run_id for comparison
                AppState.lastResults = results;
                
                showToast('success', 'Pipeline completed successfully!');
                
                // Update dashboard with new results
                updateDashboard();
                
                // Close modal after a delay
                setTimeout(() => {
                    closePipelineModal();
                }, 2000);
                
                return;
            }

            if (status.status === 'failed') {
                AppState.pipelineRunning = false;
                document.getElementById('runPipelineBtn').disabled = false;
                showToast('error', `Pipeline failed: ${status.error || 'Unknown error'}`);
                return;
            }

            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 5000); // Poll every 5 seconds
            } else {
                showToast('error', 'Pipeline took too long. Please check manually.');
                AppState.pipelineRunning = false;
                document.getElementById('runPipelineBtn').disabled = false;
            }
        } catch (error) {
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 5000);
            } else {
                showToast('error', 'Failed to get pipeline status');
                AppState.pipelineRunning = false;
                document.getElementById('runPipelineBtn').disabled = false;
            }
        }
    };

    poll();
}

function updatePipelineProgress(status) {
    const progress = status.progress || '';
    document.getElementById('progressStatus').textContent = progress;

    // Update step indicators based on progress text
    const steps = [
        { id: 'step1', keywords: ['parsing', 'agent 1', 'parse'] },
        { id: 'step2', keywords: ['matching', 'agent 2', 'score'] },
        { id: 'step3', keywords: ['ranking', 'agent 3', 'rank'] },
        { id: 'step4', keywords: ['report', 'agent 4', 'generat'] },
    ];

    const progressLower = progress.toLowerCase();
    let currentStep = 0;

    steps.forEach((step, index) => {
        const stepEl = document.getElementById(step.id);
        if (step.keywords.some(kw => progressLower.includes(kw))) {
            stepEl.classList.add('active');
            currentStep = index + 1;
        } else if (index < currentStep) {
            stepEl.classList.add('completed');
            stepEl.classList.remove('active');
        }
    });

    // Update progress bar
    const progressPercent = (currentStep / 4) * 100;
    document.getElementById('progressBar').style.width = `${progressPercent}%`;
}

// ═══════════════════════════════════════════
// Results Functions
// ═══════════════════════════════════════════

async function viewRunResults(runId) {
    try {
        const results = await API.getCandidates(runId);
        results.run_id = runId; // Store run_id for comparison
        AppState.lastResults = results;
        AppState.currentRunId = runId;
        
        displayResults(results);
        navigateToPage('results');
        updateDashboard();
    } catch (error) {
        showToast('error', 'Failed to load results');
    }
}

function displayResults(results) {
    // Show executive summary
    const summaryContainer = document.getElementById('executiveSummary');
    if (results.executive_summary) {
        summaryContainer.style.display = 'block';
        document.getElementById('executiveSummaryText').textContent = results.executive_summary;
    } else {
        summaryContainer.style.display = 'none';
    }

    // Display candidates
    const container = document.getElementById('candidatesList');
    
    if (!results.ranked_candidates || results.ranked_candidates.length === 0) {
        container.innerHTML = `
            <div class="empty-state-card">
                <span class="empty-icon">🔍</span>
                <h3>No Results Yet</h3>
                <p>Run the pipeline to see candidate rankings</p>
            </div>
        `;
        return;
    }

    container.innerHTML = results.ranked_candidates.map(candidate => `
        <div class="candidate-card ${candidate.status?.toLowerCase() || ''}">
            <div class="candidate-header">
                <div class="candidate-info">
                    <h3>${candidate.name || 'Unknown'}</h3>
                    ${candidate.email ? `<div class="candidate-email">📧 ${candidate.email}</div>` : ''}
                </div>
                <div class="score-section">
                    <div class="score-value">${candidate.score || 0}</div>
                    <div class="score-rank">Rank #${candidate.rank || 'N/A'}</div>
                </div>
            </div>
            
            <div class="candidate-meta">
                ${candidate.matched_skills ? `
                    <div class="meta-item">
                        <span>✅</span>
                        <span>${candidate.matched_skills.length} skills matched</span>
                    </div>
                ` : ''}
                ${candidate.missing_skills ? `
                    <div class="meta-item">
                        <span>⚠️</span>
                        <span>${candidate.missing_skills.length} skills missing</span>
                    </div>
                ` : ''}
                ${candidate.experience_years ? `
                    <div class="meta-item">
                        <span>💼</span>
                        <span>${candidate.experience_years} years exp.</span>
                    </div>
                ` : ''}
            </div>

            ${candidate.matched_skills || candidate.missing_skills ? `
                <div class="skills-match">
                    ${candidate.matched_skills ? candidate.matched_skills.map(skill => 
                        `<span class="skill-tag matched">+${skill}</span>`
                    ).join('') : ''}
                    ${candidate.missing_skills ? candidate.missing_skills.map(skill => 
                        `<span class="skill-tag missing">-${skill}</span>`
                    ).join('') : ''}
                </div>
            ` : ''}

            ${candidate.reasoning ? `
                <div class="candidate-reasoning">
                    "${candidate.reasoning}"
                </div>
            ` : ''}
        </div>
    `).join('');
}

function viewReport() {
    if (!AppState.currentRunId) {
        showToast('warning', 'No report available');
        return;
    }
    window.open(API.getReport(AppState.currentRunId), '_blank');
}

function downloadReport() {
    if (!AppState.currentRunId) {
        showToast('warning', 'No report available');
        return;
    }
    const link = document.createElement('a');
    link.href = API.getReport(AppState.currentRunId);
    link.download = `report_${AppState.currentRunId}.html`;
    link.target = '_blank';
    link.click();
}

// ═══════════════════════════════════════════
// History Functions
// ═══════════════════════════════════════════

async function loadHistory() {
    try {
        const data = await API.getRuns();
        const container = document.getElementById('historyList');

        if (!data.runs || data.runs.length === 0) {
            container.innerHTML = `
                <div class="empty-state-card">
                    <span class="empty-icon">📜</span>
                    <h3>No History</h3>
                    <p>Pipeline runs will appear here</p>
                </div>
            `;
            return;
        }

        container.innerHTML = data.runs.map(run => `
            <div class="history-item">
                <div class="history-item-info">
                    <h4>Run: ${run.run_id}</h4>
                    <span>${formatDate(run.started_at)} · ${run.progress || 'N/A'}</span>
                </div>
                <div>
                    <span class="status-badge ${run.status}">${run.status}</span>
                    ${run.status === 'completed' ? `
                        <button class="btn btn-sm btn-secondary" onclick="viewRunResults('${run.run_id}')" style="margin-left: 8px;">
                            View
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// ═══════════════════════════════════════════
// Initialization
// ═══════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Initialize navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navigateToPage(item.dataset.page);
        });
    });

    // Initialize drop zone
    initDropZone();

    // Initialize job description form
    document.getElementById('jobDescriptionForm').addEventListener('submit', saveJobDescription);

    // Initialize run pipeline button
    document.getElementById('runPipelineBtn').addEventListener('click', runPipeline);

    // Load initial data
    loadJobInfo();
    updateDashboard();
    loadHistory();

    // Check API health
    API.healthCheck().catch(() => {
        document.querySelector('.status-dot').classList.remove('online');
        showToast('warning', 'Server connection issues detected');
    });
});

// Make functions globally available
window.navigateToPage = navigateToPage;
window.removeFile = removeFile;
window.uploadFiles = uploadFiles;
window.clearUploads = clearUploads;
window.loadDefaultJob = loadDefaultJob;
window.runPipeline = runPipeline;
window.closePipelineModal = closePipelineModal;
window.viewRunResults = viewRunResults;
window.viewReport = viewReport;
window.downloadReport = downloadReport;