// Authentication and user management JavaScript

// Check authentication status on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
    updateNavbar();
});

function checkAuthStatus() {
    const token = localStorage.getItem('token');
    const currentPage = window.location.pathname;
    
    // Pages that require authentication
    const protectedPages = ['/dashboard', '/candidate', '/hr', '/resumes', '/profile'];
    
    // Pages that should redirect if already authenticated
    const publicPages = ['/login', '/register'];
    
    if (!token && protectedPages.some(page => currentPage.startsWith(page))) {
        // Redirect to login if not authenticated and trying to access protected page
        window.location.href = '/login';
        return;
    }
    
    if (token && publicPages.some(page => currentPage.startsWith(page))) {
        // Redirect to dashboard if authenticated and trying to access login/register
        redirectToDashboard();
        return;
    }
    
    // Verify token validity if present
    if (token) {
        verifyToken();
    }
}

async function verifyToken() {
    const token = localStorage.getItem('token');
    
    try {
        const response = await fetch('/api/auth/user', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) {
            // Token is invalid, clear storage and redirect to login
            clearAuthData();
            if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        } else {
            const data = await response.json();
            localStorage.setItem('user', JSON.stringify(data.user));
        }
    } catch (error) {
        console.error('Token verification failed:', error);
    }
}

function updateNavbar() {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const navbarUser = document.getElementById('navbarUser');
    
    if (!navbarUser) return;
    
    if (token && user.name) {
        // Create avatar element based on auth provider
        const avatarElement = user.github_avatar 
            ? `<img src="${user.github_avatar}" alt="Avatar" class="rounded-circle me-1" width="22" height="22">` 
            : `<i class="fas fa-user me-1"></i>`;
            
        navbarUser.innerHTML = `
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown">
                    ${avatarElement}${user.name}
                </a>
                <ul class="dropdown-menu">
                    <li><a class="dropdown-item" href="/profile">
                        <i class="fas fa-user me-2"></i>Profile
                    </a></li>
                    <li><a class="dropdown-item" href="/dashboard">
                        <i class="fas fa-tachometer-alt me-2"></i>Dashboard
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="#" onclick="logout()">
                        <i class="fas fa-sign-out-alt me-2"></i>Logout
                    </a></li>
                </ul>
            </li>
        `;
    } else {
        // When user is not authenticated, show empty navbar
        navbarUser.innerHTML = '';
    }
}

function redirectToDashboard() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    if (user.role === 'hr') {
        window.location.href = '/hr';
    } else {
        window.location.href = '/candidate';
    }
}

function logout() {
    clearAuthData();
    showAlert('You have been logged out successfully', 'success');
    window.location.href = '/';
}

function clearAuthData() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}

// Helper function to get authorization headers
function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}
