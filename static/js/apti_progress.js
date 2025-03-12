document.addEventListener('DOMContentLoaded', function() {
    initializeProgress();
    loadProgress();
});

function initializeProgress() {
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach((row) => {
        const problemId = row.getAttribute('data-problem-id');
        const buttonCell = document.createElement('td');
        const button = document.createElement('button');
        button.className = 'btn btn-default btn-sm';
        button.innerHTML = 'Mark Complete';
        button.onclick = function() {
            toggleProblemStatus(problemId);
        };
        buttonCell.appendChild(button);
        row.appendChild(buttonCell);
    });
}

function toggleProblemStatus(problemId) {
    fetch('/update_aptitude_progress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            problem_id: problemId,
            status: true
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateButtonStatus(problemId, true);
            updateProgressDisplay();
        } else {
            console.error('Failed to update progress:', data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function loadProgress() {
    fetch('/get_aptitude_progress')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Object.entries(data.progress).forEach(([problemId, isCompleted]) => {
                    if (isCompleted) {
                        updateButtonStatus(problemId, true);
                    }
                });
                updateProgressDisplay();
            }
        })
        .catch(error => {
            console.error('Error loading progress:', error);
        });
}

function updateButtonStatus(problemId, completed) {
    const row = document.querySelector(`tr[data-problem-id="${problemId}"]`);
    if (row) {
        const button = row.querySelector('button');
        if (completed) {
            button.className = 'btn btn-success btn-sm';
            button.innerHTML = 'Completed';
        } else {
            button.className = 'btn btn-default btn-sm';
            button.innerHTML = 'Mark Complete';
        }
    }
}

function updateProgressDisplay() {
    const totalProblems = document.querySelectorAll('tbody tr').length;
    const completedProblems = document.querySelectorAll('.btn-success').length;
    
    const topicProgress = document.getElementById('topic-progress');
    const topicProgressBar = document.getElementById('topic-progress-bar');
    const overallProgress = document.getElementById('overall-progress');
    const overallProgressBar = document.getElementById('overall-progress-bar');
    
    if (topicProgress && topicProgressBar) {
        topicProgress.textContent = `${completedProblems}/${totalProblems}`;
        const percentage = (completedProblems / totalProblems) * 100;
        topicProgressBar.style.width = `${percentage}%`;
        topicProgressBar.setAttribute('aria-valuenow', percentage);
    }
    
    // Update overall progress (you may want to fetch this from the server)
    fetch('/get_progress')
        .then(response => response.json())
        .then(data => {
            if (data.Aptitude !== undefined && overallProgress && overallProgressBar) {
                overallProgress.textContent = `${Math.round(data.Aptitude)}%`;
                overallProgressBar.style.width = `${data.Aptitude}%`;
                overallProgressBar.setAttribute('aria-valuenow', data.Aptitude);
            }
        })
        .catch(error => {
            console.error('Error updating overall progress:', error);
        });
} 