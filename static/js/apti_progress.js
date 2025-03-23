// Initialize progress tracking on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeProgress();
});

// Main initialization function
async function initializeProgress() {
    // Determine topic ID from the problem IDs on the page
    const topicId = getTopicId();
    if (!topicId) return;

    // Add event listeners to all toggle buttons
    setupToggleButtons(topicId);
    
    // Load student progress
    await loadProgress();
}

// Get topic ID based on problem prefixes
function getTopicId() {
    const firstProblem = document.querySelector('[data-problem-id]');
    if (!firstProblem) return null;
    
    const problemId = firstProblem.getAttribute('data-problem-id');
    // q prefix = Quantitative (topic_id: 11)
    // n prefix = Numbers (topic_id: 12)
    return problemId.startsWith('q') ? 11 : 12;
}

// Setup event listeners for all toggle buttons
function setupToggleButtons(topicId) {
    const toggleButtons = document.querySelectorAll('.btn-toggle');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const problemId = this.closest('[data-problem-id]').getAttribute('data-problem-id');
            const currentStatus = this.classList.contains('btn-success');
            
            // Toggle button appearance immediately for better UX
            toggleButtonStatus(this, !currentStatus);
            
            // Update server
            toggleProblemStatus(problemId, topicId, !currentStatus);
        });
    });
}

// Toggle problem completion status
async function toggleProblemStatus(problemId, topicId, status) {
    try {
        const response = await fetch('/update_aptitude_progress', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                problem_id: problemId,
                topic_id: topicId,
                status: status
            })
        });

        const data = await response.json();
        
        if (data.success) {
            // Update progress display
            updateProgressDisplay(data.completed_count, data.total_questions);
        } else {
            console.error('Failed to update progress:', data.message);
            // Revert button if update failed
            const button = document.querySelector(`[data-problem-id="${problemId}"] .btn-toggle`);
            if (button) toggleButtonStatus(button, !status);
        }
    } catch (error) {
        console.error('Error updating progress:', error);
    }
}

// Load student progress from server
async function loadProgress() {
    try {
        const response = await fetch('/get_aptitude_progress');
        const data = await response.json();
        
        if (data.success) {
            // Update all buttons based on saved progress
            Object.entries(data.progress).forEach(([problemId, isCompleted]) => {
                const button = document.querySelector(`[data-problem-id="${problemId}"] .btn-toggle`);
                if (button) toggleButtonStatus(button, isCompleted);
            });
            
            // Update progress display
            if (data.overall_progress) {
                updateProgressDisplay(data.overall_progress.completed, data.overall_progress.total);
            }
        } else {
            console.error('Failed to load progress:', data.message);
        }
    } catch (error) {
        console.error('Error loading progress:', error);
    }
}

// Update button appearance
function toggleButtonStatus(button, isCompleted) {
    if (isCompleted) {
        button.classList.remove('btn-primary');
        button.classList.add('btn-success');
        button.textContent = 'Completed';
    } else {
        button.classList.remove('btn-success');
        button.classList.add('btn-primary');
        button.textContent = 'Mark Complete';
    }
}

// Update progress display
function updateProgressDisplay(completed, total) {
    const progressBar = document.getElementById('topic-progress-bar');
    const completedCount = document.getElementById('completed-count');
    const totalCount = document.getElementById('total-count');
    
    if (progressBar && completedCount && totalCount) {
        const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
        
        progressBar.style.width = `${percentage}%`;
        progressBar.textContent = `${percentage}%`;
        
        completedCount.textContent = completed;
        totalCount.textContent = total;
    }
} 