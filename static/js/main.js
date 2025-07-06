// Main JavaScript functionality

// Global alert function
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;
    
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" id="${alertId}" role="alert">
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto-remove alert after duration
    if (duration > 0) {
        setTimeout(() => {
            const alertElement = document.getElementById(alertId);
            if (alertElement) {
                const alert = new bootstrap.Alert(alertElement);
                alert.close();
            }
        }, duration);
    }
}

// Expose the displayJobs function to the global scope for use in jobs.html
window.displayJobs = function(jobs, container) {
    // Clear the container first
    container = container || document.getElementById('jobsList');
    if (!container) return;

    // Check if there are any jobs to display
    if (!jobs || jobs.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <div class="d-flex flex-column align-items-center">
                    <i class="fas fa-search fa-3x text-muted mb-3"></i>
                    <h4>No jobs found</h4>
                    <p class="text-muted">Try adjusting your search filters</p>
                </div>
            </div>
        `;
        return;
    }

    // Build the HTML for all jobs
    let jobsHTML = '';
    jobs.forEach(job => {
        const jobTypeClass = getJobTypeBadgeClass(job.employment_type);
        const salaryDisplay = job.salary_min || job.salary_max ? 
            `$${job.salary_min || 0} - $${job.salary_max || ''}` : 
            'Not disclosed';

        jobsHTML += `
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <h5 class="card-title mb-1">${job.title}</h5>
                            <span class="badge ${jobTypeClass}">${job.employment_type}</span>
                        </div>
                        <h6 class="card-subtitle mb-2 text-muted">${job.company} - ${job.location}</h6>
                        
                        <div class="my-3">
                            <p class="card-text text-truncate-3">${job.description}</p>
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center mt-auto">
                            <small class="text-muted">
                                <i class="far fa-clock me-1"></i>${timeAgo(new Date(job.created_at))}
                            </small>
                            <div>
                                <button class="btn btn-sm btn-outline-primary" onclick="viewJobDetails(${job.id})">
                                    <i class="fas fa-info-circle me-1"></i>Details
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    // Update the container with the generated HTML
    container.innerHTML = `<div class="row">${jobsHTML}</div>`;
}

// Get badge class based on job type
function getJobTypeBadgeClass(type) {
    switch (type?.toLowerCase()) {
        case 'full-time': return 'bg-primary';
        case 'part-time': return 'bg-info';
        case 'contract': return 'bg-warning text-dark';
        case 'internship': return 'bg-success';
        case 'temporary': return 'bg-secondary';
        default: return 'bg-secondary';
    }
}

// Function to navigate to job details page
function viewJobDetails(jobId) {
    if (jobId) {
        window.location.href = `/jobs/${jobId}`;
    }
}

function getAlertIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'danger': return 'exclamation-triangle';
        case 'warning': return 'exclamation-circle';
        case 'info': return 'info-circle';
        default: return 'info-circle';
    }
}

// Loading spinner functions
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading...</p>
            </div>
        `;
    }
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '';
    }
}

// Format date function
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Truncate text
function truncateText(text, maxLength = 100) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Copied to clipboard!', 'success', 2000);
    }).catch(() => {
        showAlert('Failed to copy to clipboard', 'danger');
    });
}

// Validate email format
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Validate phone format
function isValidPhone(phone) {
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    return phoneRegex.test(phone.replace(/[\s\-\(\)]/g, ''));
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// API helper functions
async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('token');
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        }
    };
    
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, mergedOptions);
        
        if (response.status === 401) {
            // Unauthorized - clear auth and redirect to login
            clearAuthData();
            window.location.href = '/login';
            throw new Error('Unauthorized');
        }
        
        return response;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// File upload progress
function createFileUploadProgress(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return null;
    
    const progressHtml = `
        <div class="upload-progress">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="upload-filename">Uploading...</span>
                <span class="upload-percentage">0%</span>
            </div>
            <div class="progress">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 0%"></div>
            </div>
        </div>
    `;
    
    container.innerHTML = progressHtml;
    
    return {
        updateProgress: (percentage, filename = '') => {
            const progressBar = container.querySelector('.progress-bar');
            const percentageSpan = container.querySelector('.upload-percentage');
            const filenameSpan = container.querySelector('.upload-filename');
            
            if (progressBar) progressBar.style.width = percentage + '%';
            if (percentageSpan) percentageSpan.textContent = percentage + '%';
            if (filename && filenameSpan) filenameSpan.textContent = filename;
        },
        complete: () => {
            container.innerHTML = '';
        }
    };
}

// Form validation helper
function validateForm(formId, rules) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    const errors = [];
    
    for (const [fieldName, fieldRules] of Object.entries(rules)) {
        const field = form.querySelector(`[name="${fieldName}"], #${fieldName}`);
        if (!field) continue;
        
        const value = field.value.trim();
        
        // Clear previous validation state
        field.classList.remove('is-invalid');
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) feedback.remove();
        
        // Apply validation rules
        for (const rule of fieldRules) {
            if (rule.required && !value) {
                addFieldError(field, rule.message || `${fieldName} is required`);
                isValid = false;
                break;
            }
            
            if (rule.minLength && value.length < rule.minLength) {
                addFieldError(field, rule.message || `${fieldName} must be at least ${rule.minLength} characters`);
                isValid = false;
                break;
            }
            
            if (rule.email && value && !isValidEmail(value)) {
                addFieldError(field, rule.message || 'Please enter a valid email address');
                isValid = false;
                break;
            }
            
            if (rule.custom && !rule.custom(value)) {
                addFieldError(field, rule.message || 'Invalid value');
                isValid = false;
                break;
            }
        }
    }
    
    return isValid;
}

function addFieldError(field, message) {
    field.classList.add('is-invalid');
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    feedback.textContent = message;
    field.parentNode.appendChild(feedback);
}

// Toast notification
function showToast(message, type = 'info', duration = 5000) {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    const toastId = 'toast-' + Date.now();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, {
        delay: duration,
        autohide: true
    });
    
    bsToast.show();
    
    // Clean up after hiding
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1080';
    document.body.appendChild(container);
    return container;
}

// Job status helper functions
function getJobStatusBadge(status) {
    const statusMap = {
        'active': '<span class="badge bg-success">Active</span>',
        'inactive': '<span class="badge bg-secondary">Inactive</span>',
        'draft': '<span class="badge bg-warning">Draft</span>',
        'expired': '<span class="badge bg-danger">Expired</span>',
        'archived': '<span class="badge bg-dark">Archived</span>'
    };
    
    return statusMap[status.toLowerCase()] || `<span class="badge bg-secondary">${status}</span>`;
}

function getApplicationStatusBadge(status) {
    const statusMap = {
        'pending': '<span class="badge bg-warning">Pending</span>',
        'reviewing': '<span class="badge bg-info">Reviewing</span>',
        'interview': '<span class="badge bg-primary">Interview</span>',
        'hired': '<span class="badge bg-success">Hired</span>',
        'rejected': '<span class="badge bg-danger">Rejected</span>',
        'withdrawn': '<span class="badge bg-secondary">Withdrawn</span>'
    };
    
    return statusMap[status.toLowerCase()] || `<span class="badge bg-secondary">${status}</span>`;
}

// Initialize page-specific functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Check current page and load appropriate data
    const currentPath = window.location.pathname;
    
    // HR Dashboard page
    if (currentPath === '/hr/dashboard') {
        // Initialize charts if required
        initJobMetricsCharts();
        
        // Load initial data
        loadHRJobs();
        loadHRApplications();
        loadJobMetrics();
        
        // Set up job filter form listener
        const jobFilterForm = document.getElementById('jobFilterForm');
        if (jobFilterForm) {
            jobFilterForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(jobFilterForm);
                const filters = {};
                for (const [key, value] of formData.entries()) {
                    if (value) filters[key] = value;
                }
                loadHRJobs(1, 10, filters);
            });
        }
        
        // Set up application filter form listener
        const appFilterForm = document.getElementById('appFilterForm');
        if (appFilterForm) {
            appFilterForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(appFilterForm);
                const filters = {};
                for (const [key, value] of formData.entries()) {
                    if (value) filters[key] = value;
                }
                loadHRApplications(1, 10, filters);
            });
        }
        
        // Set up job search
        const jobSearchInput = document.getElementById('jobSearchInput');
        if (jobSearchInput) {
            jobSearchInput.addEventListener('keyup', debounce(function() {
                const searchValue = jobSearchInput.value.trim();
                loadHRJobs(1, 10, { search: searchValue });
            }, 500));
        }
        
        // Set up application search
        const appSearchInput = document.getElementById('appSearchInput');
        if (appSearchInput) {
            appSearchInput.addEventListener('keyup', debounce(function() {
                const searchValue = appSearchInput.value.trim();
                loadHRApplications(1, 10, { search: searchValue });
            }, 500));
        }
        
        // Set up select all checkboxes
        const selectAllJobs = document.getElementById('selectAllJobs');
        if (selectAllJobs) {
            selectAllJobs.addEventListener('change', toggleSelectAllJobs);
        }
        
        const selectAllApps = document.getElementById('selectAllApps');
        if (selectAllApps) {
            selectAllApps.addEventListener('change', toggleSelectAllJobs);
        }
        
        // Set up tab switching to reload data
        const hrTabs = document.querySelectorAll('button[data-bs-toggle="tab"]');
        if (hrTabs) {
            hrTabs.forEach(tab => {
                tab.addEventListener('shown.bs.tab', function(event) {
                    const targetId = event.target.getAttribute('data-bs-target');
                    
                    if (targetId === '#jobs-tab') {
                        loadHRJobs();
                    } else if (targetId === '#applications-tab') {
                        loadHRApplications();
                    } else if (targetId === '#analytics-tab') {
                        loadJobMetrics();
                    }
                });
            });
        }
        
        // Setup realtime event listeners
        setupJobRealtimeEvents();
    }
    
    // Candidate Dashboard page
    if (currentPath === '/candidate/dashboard') {
        // Load candidate-specific data
        loadCandidateApplications();
        loadRecommendedJobs();
    }
    
    // Jobs page
    if (currentPath === '/jobs') {
        loadJobListings();
        
        // Set up job search & filter form
        const jobSearchForm = document.getElementById('jobSearchForm');
        if (jobSearchForm) {
            jobSearchForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(jobSearchForm);
                const filters = {};
                for (const [key, value] of formData.entries()) {
                    if (value) filters[key] = value;
                }
                loadJobListings(1, 10, filters);
            });
        }
    }
    
    // Resumes page
    if (currentPath === '/resumes') {
        loadUserResumes();
    }
});

// Function to setup realtime event listeners for job-related events
function setupJobRealtimeEvents() {
    if (typeof setupRealtimeSocket === 'function') {
        const socket = setupRealtimeSocket();
        
        if (socket) {
            // Job-related events
            socket.on('job_created', function(data) {
                showToast('A new job has been created', 'info');
                loadHRJobs();
                loadJobMetrics();
            });
            
            socket.on('job_updated', function(data) {
                showToast('A job has been updated', 'info');
                loadHRJobs();
            });
            
            socket.on('job_deleted', function(data) {
                showToast('A job has been deleted', 'info');
                loadHRJobs();
                loadJobMetrics();
            });
            
            // Application-related events
            socket.on('new_application', function(data) {
                showToast('A new application has been submitted', 'info');
                loadHRApplications();
                loadJobMetrics();
            });
            
            socket.on('application_status_changed', function(data) {
                showToast('An application status has been updated', 'info');
                loadHRApplications();
                loadJobMetrics();
            });
            
            socket.on('application_withdrawn', function(data) {
                showToast('An application has been withdrawn', 'info');
                loadHRApplications();
                loadJobMetrics();
            });
            
            socket.on('application_feedback_added', function(data) {
                showToast('Feedback has been added to an application', 'info');
                loadHRApplications();
            });
            
            socket.on('bulk_application_update', function(data) {
                showToast(`${data.count || 'Multiple'} applications have been updated`, 'info');
                loadHRApplications();
                loadJobMetrics();
            });
        }
    }
}

// Helper function for debouncing search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Function to show loader overlay
function showLoader() {
    const loaderEl = document.getElementById('pageLoader');
    if (loaderEl) loaderEl.classList.remove('d-none');
}

// Function to hide loader overlay
function hideLoader() {
    const loaderEl = document.getElementById('pageLoader');
    if (loaderEl) loaderEl.classList.add('d-none');
}

// Function to display toast notifications
function showToast(message, type = 'success') {
    // Check if the toast container exists, if not create it
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create a unique ID for this toast
    const toastId = 'toast-' + Date.now();
    
    // Create the toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast text-white bg-${type}`;
    toastEl.id = toastId;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    // Toast content
    toastEl.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">Notification</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    // Add the toast to the container
    toastContainer.appendChild(toastEl);
    
    // Initialize the Bootstrap toast and show it
    const toastObj = new bootstrap.Toast(toastEl, {
        delay: 5000
    });
    toastObj.show();
    
    // Remove the toast element when hidden
    toastEl.addEventListener('hidden.bs.toast', function () {
        toastEl.remove();
    });
}

// Function to send realtime notifications
function sendRealtimeNotification(eventType, data) {
    if (typeof socket !== 'undefined' && socket) {
        socket.emit('event', {
            type: eventType,
            data: data
        });
    }
}

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Job filtering and loading function
function loadHRJobs(page = 1, limit = 10, filters = {}) {
    // Build query parameters
    let params = new URLSearchParams();
    params.append('page', page);
    params.append('limit', limit);
    
    // Add any filters
    Object.keys(filters).forEach(key => {
        if (filters[key]) {
            params.append(key, filters[key]);
        }
    });
    
    showLoader();
    
    // Call API endpoint
    fetch(`/api/hr/jobs?${params.toString()}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load jobs');
            return response.json();
        })
        .then(data => {
            const jobsTable = document.getElementById('hrJobsTable');
            const jobsTableBody = document.getElementById('hrJobsTableBody');
            const paginationContainer = document.getElementById('hrJobsPagination');
            
            if (!jobsTableBody) return;
            
            // Clear existing table
            jobsTableBody.innerHTML = '';
            
            // Check if jobs exist
            if (data.jobs && data.jobs.length > 0) {
                // Add jobs to table
                data.jobs.forEach(job => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>
                            <div class="form-check">
                                <input class="form-check-input job-checkbox" type="checkbox" value="${job.id}" id="job-${job.id}">
                            </div>
                        </td>
                        <td>${job.id}</td>
                        <td>${job.title}</td>
                        <td>${job.company}</td>
                        <td>${job.location}</td>
                        <td><span class="badge bg-${job.is_active ? 'success' : 'secondary'}">${job.is_active ? 'Active' : 'Inactive'}</span></td>
                        <td>${formatDate(job.created_at)}</td>
                        <td>${job.applications_count || 0}</td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-primary" onclick="editHRJob(${job.id})">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-outline-danger" onclick="confirmDeleteJob(${job.id})">
                                    <i class="fas fa-trash"></i>
                                </button>
                                <button class="btn btn-outline-${job.is_active ? 'warning' : 'success'}" onclick="toggleJobStatus(${job.id}, ${!job.is_active})">
                                    <i class="fas fa-${job.is_active ? 'pause' : 'play'}"></i>
                                </button>
                            </div>
                        </td>
                    `;
                    jobsTableBody.appendChild(row);
                });
                
                // Update pagination
                if (paginationContainer) {
                    paginationContainer.innerHTML = '';
                    const totalPages = Math.ceil(data.total / limit);
                    
                    // Previous button
                    const prevLi = document.createElement('li');
                    prevLi.className = `page-item ${page === 1 ? 'disabled' : ''}`;
                    prevLi.innerHTML = `<a class="page-link" href="#" onclick="loadHRJobs(${page-1}, ${limit}, ${JSON.stringify(filters)}); return false;">Previous</a>`;
                    paginationContainer.appendChild(prevLi);
                    
                    // Page numbers
                    for (let i = 1; i <= totalPages; i++) {
                        const li = document.createElement('li');
                        li.className = `page-item ${page === i ? 'active' : ''}`;
                        li.innerHTML = `<a class="page-link" href="#" onclick="loadHRJobs(${i}, ${limit}, ${JSON.stringify(filters)}); return false;">${i}</a>`;
                        paginationContainer.appendChild(li);
                    }
                    
                    // Next button
                    const nextLi = document.createElement('li');
                    nextLi.className = `page-item ${page === totalPages ? 'disabled' : ''}`;
                    nextLi.innerHTML = `<a class="page-link" href="#" onclick="loadHRJobs(${page+1}, ${limit}, ${JSON.stringify(filters)}); return false;">Next</a>`;
                    paginationContainer.appendChild(nextLi);
                }
                
                // Show the table
                jobsTable.classList.remove('d-none');
                document.getElementById('noJobsMessage').classList.add('d-none');
            } else {
                // No jobs found
                jobsTable.classList.add('d-none');
                document.getElementById('noJobsMessage').classList.remove('d-none');
            }
            
            hideLoader();
        })
        .catch(error => {
            console.error('Error loading HR jobs:', error);
            showToast('Error loading jobs. Please try again.', 'danger');
            hideLoader();
        });
}

// Function to create a new job
function createHRJob() {
    const form = document.getElementById('createJobForm');
    
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return;
    }
    
    // Get form data
    const formData = new FormData(form);
    const jobData = {};
    
    formData.forEach((value, key) => {
        jobData[key] = value;
    });
    
    // Add any missing fields with defaults
    jobData.is_active = true;
    
    showLoader();
    
    // Send API request
    fetch('/api/hr/jobs', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(jobData)
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to create job');
        return response.json();
    })
    .then(data => {
        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('createJobModal'));
        modal.hide();
        form.reset();
        form.classList.remove('was-validated');
        
        // Refresh jobs
        loadHRJobs();
        loadJobMetrics();
        
        // Show success message
        showToast('Job created successfully!', 'success');
        
        // Trigger notification for the real-time system
        sendRealtimeNotification('job_created', { job_id: data.id });
        
        hideLoader();
    })
    .catch(error => {
        console.error('Error creating job:', error);
        showToast('Error creating job. Please try again.', 'danger');
        hideLoader();
    });
}

// Function to edit job
function editHRJob(jobId) {
    showLoader();
    
    // Get job details
    fetch(`/api/hr/jobs/${jobId}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load job details');
            return response.json();
        })
        .then(job => {
            // Populate form fields
            document.getElementById('editJobId').value = job.id;
            document.getElementById('editJobTitle').value = job.title;
            document.getElementById('editJobCompany').value = job.company;
            document.getElementById('editJobLocation').value = job.location;
            document.getElementById('editJobType').value = job.type;
            document.getElementById('editJobCategory').value = job.category;
            document.getElementById('editMinSalary').value = job.min_salary || '';
            document.getElementById('editMaxSalary').value = job.max_salary || '';
            document.getElementById('editJobDescription').value = job.description;
            document.getElementById('editJobRequirements').value = job.requirements;
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('editJobModal'));
            modal.show();
            
            hideLoader();
        })
        .catch(error => {
            console.error('Error loading job details:', error);
            showToast('Error loading job details. Please try again.', 'danger');
            hideLoader();
        });
}

// Function to update job
function updateHRJob() {
    const form = document.getElementById('editJobForm');
    
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return;
    }
    
    const jobId = document.getElementById('editJobId').value;
    
    // Gather form data
    const jobData = {
        title: document.getElementById('editJobTitle').value,
        company: document.getElementById('editJobCompany').value,
        location: document.getElementById('editJobLocation').value,
        type: document.getElementById('editJobType').value,
        category: document.getElementById('editJobCategory').value,
        min_salary: document.getElementById('editMinSalary').value || null,
        max_salary: document.getElementById('editMaxSalary').value || null,
        description: document.getElementById('editJobDescription').value,
        requirements: document.getElementById('editJobRequirements').value
    };
    
    showLoader();
    
    // Send API request
    fetch(`/api/hr/jobs/${jobId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(jobData)
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to update job');
        return response.json();
    })
    .then(data => {
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('editJobModal'));
        modal.hide();
        form.classList.remove('was-validated');
        
        // Refresh jobs
        loadHRJobs();
        
        // Show success message
        showToast('Job updated successfully!', 'success');
        
        // Trigger notification for the real-time system
        sendRealtimeNotification('job_updated', { job_id: jobId });
        
        hideLoader();
    })
    .catch(error => {
        console.error('Error updating job:', error);
        showToast('Error updating job. Please try again.', 'danger');
        hideLoader();
    });
}

// Function to confirm job deletion
function confirmDeleteJob(jobId) {
    if (confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
        deleteJob(jobId);
    }
}

// Function to delete job
function deleteJob(jobId) {
    showLoader();
    
    fetch(`/api/hr/jobs/${jobId}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to delete job');
        return response.json();
    })
    .then(() => {
        // Refresh jobs
        loadHRJobs();
        loadJobMetrics();
        
        // Show success message
        showToast('Job deleted successfully!', 'success');
        
        // Trigger notification for the real-time system
        sendRealtimeNotification('job_deleted', { job_id: jobId });
        
        hideLoader();
    })
    .catch(error => {
        console.error('Error deleting job:', error);
        showToast('Error deleting job. Please try again.', 'danger');
        hideLoader();
    });
}

// Function to toggle job status (active/inactive)
function toggleJobStatus(jobId, activate) {
    showLoader();
    
    fetch(`/api/hr/jobs/${jobId}/status`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_active: activate })
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to update job status');
        return response.json();
    })
    .then(() => {
        // Refresh jobs
        loadHRJobs();
        loadJobMetrics();
        
        // Show success message
        showToast(`Job ${activate ? 'activated' : 'deactivated'} successfully!`, 'success');
        
        hideLoader();
    })
    .catch(error => {
        console.error('Error updating job status:', error);
        showToast('Error updating job status. Please try again.', 'danger');
        hideLoader();
    });
}

// Function to load job metrics and analytics
function loadJobMetrics() {
    const metricsContainer = document.getElementById('jobMetricsContainer');
    if (!metricsContainer) return; // Not on HR dashboard
    
    showLoader();
    
    // Get time range from select
    const timeRange = document.getElementById('metricsTimeRange').value || '30d';
    
    fetch(`/api/jobs/hr/metrics?time_range=${timeRange}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load job metrics');
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || 'Failed to load job metrics');
            }
            
            const metrics = data.metrics;
            
            // Update applications over time chart
            updateApplicationsOverTimeChart(metrics.applications_daily);
            
            // Update status breakdown chart
            updateStatusBreakdownChart(metrics.status_breakdown);
            
            // Update category performance table
            updateCategoryPerformanceTable(metrics.category_performance);
            
            // Update top performing jobs table
            updateTopPerformingJobsTable(metrics.top_performing_jobs);
            
            hideLoader();
        })
        .catch(error => {
            console.error('Error loading job metrics:', error);
            showToast('Error retrieving job metrics. Please try again.', 'danger');
            hideLoader();
        });
}

// Function to update the applications over time chart
function updateApplicationsOverTimeChart(dailyData) {
    const ctx = document.getElementById('applicationsTimeChart');
    if (!ctx) return;
    
    // Convert data to arrays for Chart.js
    const dates = Object.keys(dailyData).sort();
    const counts = dates.map(date => dailyData[date]);
    
    // Format dates for display
    const formattedDates = dates.map(date => {
        const d = new Date(date);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    if (window.applicationsTimeChart) {
        // Update existing chart
        window.applicationsTimeChart.data.labels = formattedDates;
        window.applicationsTimeChart.data.datasets[0].data = counts;
        window.applicationsTimeChart.update();
    } else {
        // Create new chart
        window.applicationsTimeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: formattedDates,
                datasets: [{
                    label: 'Applications',
                    data: counts,
                    fill: true,
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: 'rgba(102, 126, 234, 1)',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(tooltipItems) {
                                return formattedDates[tooltipItems[0].dataIndex];
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
}

// Function to update the status breakdown chart
function updateStatusBreakdownChart(statusData) {
    const ctx = document.getElementById('statusBreakdownChart');
    if (!ctx) return;
    
    // Convert data for Chart.js
    const labels = Object.keys(statusData).map(status => 
        status.charAt(0).toUpperCase() + status.slice(1)
    );
    const counts = Object.values(statusData);
    
    // Define status colors
    const statusColors = {
        'pending': 'rgba(108, 117, 125, 0.8)',
        'reviewing': 'rgba(255, 193, 7, 0.8)',
        'interview': 'rgba(13, 110, 253, 0.8)',
        'hired': 'rgba(25, 135, 84, 0.8)',
        'rejected': 'rgba(220, 53, 69, 0.8)'
    };
    
    // Map colors to statuses
    const backgroundColors = Object.keys(statusData).map(status => 
        statusColors[status.toLowerCase()] || 'rgba(108, 117, 125, 0.8)'
    );
    
    if (window.statusBreakdownChart) {
        // Update existing chart
        window.statusBreakdownChart.data.labels = labels;
        window.statusBreakdownChart.data.datasets[0].data = counts;
        window.statusBreakdownChart.data.datasets[0].backgroundColor = backgroundColors;
        window.statusBreakdownChart.update();
    } else {
        // Create new chart
        window.statusBreakdownChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: backgroundColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                },
                cutout: '70%'
            }
        });
    }
}

// Function to update category performance table
function updateCategoryPerformanceTable(categoryData) {
    const tableBody = document.getElementById('categoryPerformanceTable');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    if (categoryData.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="4" class="text-center">No category data available</td></tr>`;
        return;
    }
    
    categoryData.forEach(category => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${category.category}</td>
            <td>${category.jobs}</td>
            <td>${category.applications}</td>
            <td>${category.applications_per_job}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Function to update top performing jobs table
function updateTopPerformingJobsTable(jobsData) {
    const tableBody = document.getElementById('topJobsTable');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    if (jobsData.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="3" class="text-center">No job data available</td></tr>`;
        return;
    }
    
    jobsData.forEach(job => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${job.title}</td>
            <td>${job.application_count}</td>
            <td>
                <a href="/jobs/${job.id}" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-eye"></i>
                </a>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// Initialize charts for job metrics
function initJobMetricsCharts() {
    const applicationsTimeChartCtx = document.getElementById('applicationsTimeChart');
    const statusBreakdownChartCtx = document.getElementById('statusBreakdownChart');
    
    if (applicationsTimeChartCtx) {
        window.applicationsTimeChart = new Chart(applicationsTimeChartCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Applications',
                    data: [],
                    fill: true,
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: 'rgba(102, 126, 234, 1)',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(tooltipItems) {
                                return tooltipItems[0].label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    
    if (statusBreakdownChartCtx) {
        window.statusBreakdownChart = new Chart(statusBreakdownChartCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#5a5c69', '#858796'
                    ],
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                }
            }
        });
    }
}

// Function to handle bulk job actions
function bulkJobAction(action) {
    const selectedJobs = Array.from(document.querySelectorAll('.job-checkbox:checked')).map(cb => cb.value);
    
    if (selectedJobs.length === 0) {
        showToast('No jobs selected. Please select at least one job.', 'warning');
        return;
    }
    
    let endpoint;
    let actionName;
    let method = 'POST';
    let actionPayload = { job_ids: selectedJobs };
    
    switch(action) {
        case 'activate':
            endpoint = '/api/hr/jobs/bulk/activate';
            actionName = 'activate';
            break;
        case 'deactivate':
            endpoint = '/api/hr/jobs/bulk/deactivate';
            actionName = 'deactivate';
            break;
        case 'delete':
            if (!confirm(`Are you sure you want to delete ${selectedJobs.length} job(s)? This action cannot be undone.`)) {
                return;
            }
            endpoint = '/api/hr/jobs/bulk/delete';
            actionName = 'delete';
            break;
        default:
            showToast('Invalid action', 'danger');
            return;
    }
    
    showLoader();
    
    fetch(endpoint, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(actionPayload)
    })
    .then(response => {
        if (!response.ok) throw new Error(`Failed to ${actionName} jobs`);
        return response.json();
    })
    .then(data => {
        // Refresh jobs
        loadHRJobs();
        loadJobMetrics();
        
        // Show success message
        showToast(`Successfully ${actionName}d ${data.affected_count} job(s)`, 'success');
        
        // Uncheck "select all" checkbox
        const selectAllCheckbox = document.getElementById('selectAllJobs');
        if (selectAllCheckbox) selectAllCheckbox.checked = false;
        
        hideLoader();
    })
    .catch(error => {
        console.error(`Error ${actionName}ing jobs:`, error);
        showToast(`Error ${actionName}ing jobs. Please try again.`, 'danger');
        hideLoader();
    });
}

// Function to toggle select all jobs checkboxes
function toggleSelectAllJobs() {
    const selectAllCheckbox = document.getElementById('selectAllJobs');
    const jobCheckboxes = document.querySelectorAll('.job-checkbox');
    
    jobCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
}

// Function to load HR applications
function loadHRApplications(page = 1, limit = 10, filters = {}) {
    // Build query parameters
    let params = new URLSearchParams();
    params.append('page', page);
    params.append('limit', limit);
    
    // Add any filters
    Object.keys(filters).forEach(key => {
        if (filters[key]) {
            params.append(key, filters[key]);
        }
    });
    
    showLoader();
    
    // Call API endpoint
    fetch(`/api/hr/applications?${params.toString()}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load applications');
            return response.json();
        })
        .then(data => {
            const appsTable = document.getElementById('hrApplicationsTable');
            const appsTableBody = document.getElementById('hrApplicationsTableBody');
            const paginationContainer = document.getElementById('hrApplicationsPagination');
            
            if (!appsTableBody) return;
            
            // Clear existing table
            appsTableBody.innerHTML = '';
            
            // Check if applications exist
            if (data.applications && data.applications.length > 0) {
                // Add applications to table
                data.applications.forEach(app => {
                    const row = document.createElement('tr');
                    
                    // Determine status badge class
                    let statusBadgeClass = 'secondary';
                    switch (app.status) {
                        case 'pending': statusBadgeClass = 'warning'; break;
                        case 'reviewed': statusBadgeClass = 'info'; break;
                        case 'interview': statusBadgeClass = 'primary'; break;
                        case 'offered': statusBadgeClass = 'success'; break;
                        case 'rejected': statusBadgeClass = 'danger'; break;
                        case 'withdrawn': statusBadgeClass = 'dark'; break;
                    }
                    
                    row.innerHTML = `
                        <td>
                            <div class="form-check">
                                <input class="form-check-input app-checkbox" type="checkbox" value="${app.id}" id="app-${app.id}">
                            </div>
                        </td>
                        <td>${app.id}</td>
                        <td>${app.candidate_name || 'N/A'}</td>
                        <td>${app.job_title || 'N/A'}</td>
                        <td><span class="badge bg-${statusBadgeClass}">${app.status.charAt(0).toUpperCase() + app.status.slice(1)}</span></td>
                        <td>${formatDate(app.applied_date)}</td>
                        <td>${app.match_score ? app.match_score + '%' : 'N/A'}</td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-primary" onclick="viewApplication(${app.id})">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="btn btn-outline-info dropdown-toggle" data-bs-toggle="dropdown">
                                    <i class="fas fa-cog"></i>
                                </button>
                                <ul class="dropdown-menu">
                                    <li><a class="dropdown-item" href="#" onclick="updateApplicationStatus(${app.id}, 'pending')">Mark as Pending</a></li>
                                    <li><a class="dropdown-item" href="#" onclick="updateApplicationStatus(${app.id}, 'reviewed')">Mark as Reviewed</a></li>
                                    <li><a class="dropdown-item" href="#" onclick="updateApplicationStatus(${app.id}, 'interview')">Schedule Interview</a></li>
                                    <li><a class="dropdown-item" href="#" onclick="updateApplicationStatus(${app.id}, 'offered')">Send Offer</a></li>
                                    <li><a class="dropdown-item" href="#" onclick="updateApplicationStatus(${app.id}, 'rejected')">Reject</a></li>
                                </ul>
                            </div>
                        </td>
                    `;
                    appsTableBody.appendChild(row);
                });
                
                // Update pagination
                if (paginationContainer) {
                    paginationContainer.innerHTML = '';
                    const totalPages = Math.ceil(data.total / limit);
                    
                    // Previous button
                    const prevLi = document.createElement('li');
                    prevLi.className = `page-item ${page === 1 ? 'disabled' : ''}`;
                    prevLi.innerHTML = `<a class="page-link" href="#" onclick="loadHRApplications(${page-1}, ${limit}, ${JSON.stringify(filters)}); return false;">Previous</a>`;
                    paginationContainer.appendChild(prevLi);
                    
                    // Page numbers
                    for (let i = 1; i <= totalPages; i++) {
                        const li = document.createElement('li');
                        li.className = `page-item ${page === i ? 'active' : ''}`;
                        li.innerHTML = `<a class="page-link" href="#" onclick="loadHRApplications(${i}, ${limit}, ${JSON.stringify(filters)}); return false;">${i}</a>`;
                        paginationContainer.appendChild(li);
                    }
                    
                    // Next button
                    const nextLi = document.createElement('li');
                    nextLi.className = `page-item ${page === totalPages ? 'disabled' : ''}`;
                    nextLi.innerHTML = `<a class="page-link" href="#" onclick="loadHRApplications(${page+1}, ${limit}, ${JSON.stringify(filters)}); return false;">Next</a>`;
                    paginationContainer.appendChild(nextLi);
                }
                
                // Show the table
                appsTable.classList.remove('d-none');
                document.getElementById('noAppsMessage').classList.add('d-none');
            } else {
                // No applications found
                appsTable.classList.add('d-none');
                document.getElementById('noAppsMessage').classList.remove('d-none');
            }
            
            hideLoader();
        })
        .catch(error => {
            console.error('Error loading HR applications:', error);
            showToast('Error loading applications. Please try again.', 'danger');
            hideLoader();
        });
}

// Function to view application details
function viewApplication(applicationId) {
    showLoader();
    
    fetch(`/api/hr/applications/${applicationId}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load application details');
            return response.json();
        })
        .then(app => {
            // Populate application details modal
            const modal = document.getElementById('applicationDetailModal');
            
            if (modal) {
                document.getElementById('appDetailId').textContent = app.id;
                document.getElementById('appDetailJobTitle').textContent = app.job_title || 'N/A';
                document.getElementById('appDetailCompany').textContent = app.company || 'N/A';
                document.getElementById('appDetailAppliedDate').textContent = formatDate(app.applied_date);
                document.getElementById('appDetailStatus').textContent = app.status.charAt(0).toUpperCase() + app.status.slice(1);
                
                // Set status badge color
                const statusBadge = document.getElementById('appDetailStatusBadge');
                if (statusBadge) {
                    statusBadge.className = 'badge';
                    switch (app.status) {
                        case 'pending': statusBadge.classList.add('bg-warning'); break;
                        case 'reviewed': statusBadge.classList.add('bg-info'); break;
                        case 'interview': statusBadge.classList.add('bg-primary'); break;
                        case 'offered': statusBadge.classList.add('bg-success'); break;
                        case 'rejected': statusBadge.classList.add('bg-danger'); break;
                        case 'withdrawn': statusBadge.classList.add('bg-dark'); break;
                        default: statusBadge.classList.add('bg-secondary');
                    }
                }
                
                // Show/hide withdraw button based on status
                const withdrawBtn = document.getElementById('withdrawApplicationBtn');
                if (withdrawBtn) {
                    if (app.status !== 'withdrawn') {
                        withdrawBtn.classList.remove('d-none');
                        withdrawBtn.setAttribute('onclick', `confirmWithdrawApplication(${app.id})`);
                    } else {
                        withdrawBtn.classList.add('d-none');
                    }
                }
                
                // Populate resume iframe if available
                const resumeFrame = document.getElementById('appDetailResume');
                if (resumeFrame && app.resume_url) {
                    resumeFrame.src = app.resume_url;
                    document.getElementById('appDetailResumeContainer').classList.remove('d-none');
                } else {
                    document.getElementById('appDetailResumeContainer').classList.add('d-none');
                }
                
                // Populate cover letter if available
                const coverLetterSection = document.getElementById('appDetailCoverLetterSection');
                if (coverLetterSection) {
                    if (app.cover_letter) {
                        document.getElementById('appDetailCoverLetter').textContent = app.cover_letter;
                        coverLetterSection.classList.remove('d-none');
                    } else {
                        coverLetterSection.classList.add('d-none');
                    }
                }
                
                // Populate feedback if available
                const feedbackSection = document.getElementById('appDetailFeedbackSection');
                if (feedbackSection) {
                    if (app.feedback && app.feedback.length > 0) {
                        const feedbackContainer = document.getElementById('appDetailFeedback');
                        feedbackContainer.innerHTML = '';
                        
                        app.feedback.forEach(item => {
                            const feedbackItem = document.createElement('div');
                            feedbackItem.className = 'feedback-item mb-3 p-3 bg-light rounded';
                            feedbackItem.innerHTML = `
                                <div class="small text-muted mb-1">${formatDate(item.created_at)}</div>
                                <p class="mb-0">${item.content}</p>
                            `;
                            feedbackContainer.appendChild(feedbackItem);
                        });
                        
                        feedbackSection.classList.remove('d-none');
                    } else {
                        feedbackSection.classList.add('d-none');
                    }
                }
                
                // Show the modal
                const modalObj = new bootstrap.Modal(modal);
                modalObj.show();
            }
            
            hideLoader();
        })
        .catch(error => {
            console.error('Error loading application details:', error);
            showToast('Error loading application details. Please try again.', 'danger');
            hideLoader();
        });
}

// Function to confirm withdraw application
function confirmWithdrawApplication(applicationId) {
    if (confirm('Are you sure you want to withdraw this application? This action cannot be undone.')) {
        withdrawApplication(applicationId);
    }
}

// Function to withdraw application
function withdrawApplication(applicationId) {
    showLoader();
    
    fetch(`/api/candidate/applications/${applicationId}/withdraw`, {
        method: 'PUT'
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to withdraw application');
        return response.json();
    })
    .then(() => {
        // Close modal if it's open
        const modal = document.getElementById('applicationDetailModal');
        if (modal) {
            const modalObj = bootstrap.Modal.getInstance(modal);
            if (modalObj) modalObj.hide();
        }
        
        // Refresh applications
        loadCandidateApplications();
        
        // Show success message
        showToast('Application withdrawn successfully!', 'success');
        
        hideLoader();
    })
    .catch(error => {
        console.error('Error withdrawing application:', error);
        showToast('Error withdrawing application. Please try again.', 'danger');
        hideLoader();
    });
}

// Function to load jobs on the jobs listing page
function loadJobs(page = 1) {
    // Show loading state
    const jobsListContainer = document.getElementById('jobsList');
    if (!jobsListContainer) return;

    // Display loading spinner
    jobsListContainer.innerHTML = `
        <div class="col-12 text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading jobs...</p>
        </div>
    `;

    // Get filter values
    const search = document.getElementById('searchInput')?.value || '';
    const location = document.getElementById('locationFilter')?.value || '';
    const jobType = document.getElementById('typeFilter')?.value || '';
    const minSalary = document.getElementById('minSalary')?.value || '';
    const maxSalary = document.getElementById('maxSalary')?.value || '';

    // Build query parameters
    const queryParams = new URLSearchParams({
        page: page,
        per_page: 10
    });

    if (search) queryParams.append('search', search);
    if (location) queryParams.append('location', location);
    if (jobType) queryParams.append('type', jobType);
    if (minSalary) queryParams.append('salary_min', minSalary);
    if (maxSalary) queryParams.append('salary_max', maxSalary);

    // Fetch jobs from API
    fetch(`/api/jobs/?${queryParams.toString()}`, {
        headers: getAuthHeaders()
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to load jobs');
        return response.json();
    })
    .then(data => {
        // Check if we have jobs to display
        if (!data.jobs || data.jobs.length === 0) {
            jobsListContainer.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="fas fa-search fa-3x text-muted mb-3"></i>
                    <h4 class="text-muted">No jobs found</h4>
                    <p>Try adjusting your filters or search criteria.</p>
                </div>
            `;
            return;
        }

        // Clear previous content
        jobsListContainer.innerHTML = '';

        // Display each job
        data.jobs.forEach(job => {
            // Create job card
            const jobCard = document.createElement('div');
            jobCard.className = 'col-md-6 col-lg-4 mb-4';
            
            // Format salary display
            let salaryDisplay = 'Not specified';
            if (job.min_salary && job.max_salary) {
                salaryDisplay = `$${job.min_salary.toLocaleString()} - $${job.max_salary.toLocaleString()}`;
            } else if (job.min_salary) {
                salaryDisplay = `From $${job.min_salary.toLocaleString()}`;
            } else if (job.max_salary) {
                salaryDisplay = `Up to $${job.max_salary.toLocaleString()}`;
            }
            
            // Get badge color for job type
            const badgeColor = getJobTypeBadge(job.type || 'other');
            
            jobCard.innerHTML = `
                <div class="card h-100 shadow-sm">
                    <div class="card-body">
                        <div class="d-flex justify-content-between mb-2">
                            <h5 class="card-title mb-0">${job.title}</h5>
                            <span class="badge bg-${badgeColor}">${formatJobType(job.type)}</span>
                        </div>
                        <h6 class="card-subtitle mb-2 text-muted">${job.company}</h6>
                        <p class="card-text small text-muted">
                            <i class="fas fa-map-marker-alt me-1"></i> ${job.location}
                        </p>
                        <p class="card-text small">
                            <i class="fas fa-money-bill-alt me-1"></i> ${salaryDisplay}
                        </p>
                        <p class="card-text">${job.description.substring(0, 100)}${job.description.length > 100 ? '...' : ''}</p>
                    </div>
                    <div class="card-footer bg-transparent">
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">Posted ${formatDate(job.created_at)}</small>
                            <a href="#" class="btn btn-outline-primary btn-sm" onclick="viewJobDetails(${job.id}); return false;">View Details</a>
                        </div>
                    </div>
                </div>
            `;
            
            jobsListContainer.appendChild(jobCard);
        });
        
        // Add pagination if needed
        if (data.pagination && data.pagination.total_pages > 1) {
            const paginationContainer = document.createElement('div');
            paginationContainer.className = 'col-12';
            paginationContainer.innerHTML = `
                <nav aria-label="Job listings pagination">
                    <ul class="pagination justify-content-center">
                        <li class="page-item ${data.pagination.current_page === 1 ? 'disabled' : ''}">
                            <a class="page-link" href="#" onclick="loadJobs(${data.pagination.current_page - 1}); return false;">Previous</a>
                        </li>
                        ${Array.from({length: data.pagination.total_pages}, (_, i) => i + 1)
                            .map(p => `
                                <li class="page-item ${p === data.pagination.current_page ? 'active' : ''}">
                                    <a class="page-link" href="#" onclick="loadJobs(${p}); return false;">${p}</a>
                                </li>
                            `).join('')}
                        <li class="page-item ${data.pagination.current_page === data.pagination.total_pages ? 'disabled' : ''}">
                            <a class="page-link" href="#" onclick="loadJobs(${data.pagination.current_page + 1}); return false;">Next</a>
                        </li>
                    </ul>
                </nav>
            `;
            jobsListContainer.appendChild(paginationContainer);
        }
    })
    .catch(error => {
        console.error('Error loading jobs:', error);
        jobsListContainer.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                <h4 class="text-danger">Error loading jobs</h4>
                <p>Please try again later or contact support if the problem persists.</p>
                <button class="btn btn-primary mt-3" onclick="loadJobs()">Try Again</button>
            </div>
        `;
    });
}

// Function to apply filters and reload jobs
function applyFilters() {
    loadJobs(1);
}

// Helper function to get job type badge color
function getJobTypeBadge(type) {
    if (!type) return 'secondary';
    
    switch(type.toLowerCase()) {
        case 'full-time':
        case 'fulltime':
            return 'success';
        case 'part-time':
        case 'parttime':
            return 'info';
        case 'contract':
            return 'warning';
        case 'internship':
            return 'primary';
        case 'remote':
            return 'dark';
        default:
            return 'secondary';
    }
}

// Helper function to format job type display
function formatJobType(type) {
    if (!type) return 'Other';
    
    // Convert kebab-case to Title Case
    return type
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Helper to get auth headers for API requests
function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// Helper function to get authentication token
function getAuthToken() {
    return localStorage.getItem('token') || '';
}

// Secure resume download function
async function downloadResume(resumeId) {
    try {
        const response = await fetch(`/api/resumes/${resumeId}/download`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Get the filename from the Content-Disposition header if available
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'resume.pdf';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1].replace(/['"]/g, '');
            }
        }

        // Convert response to blob
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        // Create a temporary link and trigger download
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showAlert('Resume download started', 'success');
    } catch (error) {
        console.error('Error downloading resume:', error);
        showAlert('Failed to download resume. Please try again.', 'danger');
    }
}
