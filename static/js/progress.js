// Progress tracking functionality
document.addEventListener("DOMContentLoaded", function () {
    initializeProgress();
});

function initializeProgress() {
    const rows = document.querySelectorAll("tbody tr");
    const totalProblems = rows.length;

    rows.forEach((row, index) => {
        // Create button cell
        const buttonCell = document.createElement("td");
        const button = document.createElement("button");
        button.className = "btn btn-default btn-sm";
        button.innerHTML = "Mark Complete";
        button.onclick = function () {
            toggleProblemStatus(index, getCurrentTopicId());
        };

        buttonCell.appendChild(button);
        row.appendChild(buttonCell);
    });

    // Load saved progress
    loadStudentProgress();
}

function getCurrentTopicId() {
    // Extract topic ID from URL or data attribute
    const path = window.location.pathname;
    const topicMap = {
        '/dsa_basic_program': 1,
        '/dsa_arrays_and_strings': 2,
        '/dsa/linked-lists': 3,
        '/dsa/stacks-and-queues': 4,
        '/dsa/trees-and-graphs': 5,
        '/dsa/searching-and-sorting': 6,
        '/dsa/dp-problems': 7,
        '/dsa/recursion-and-backtracking': 8,
        '/dsa/greedy-algorithms': 9,
        '/dsa/bit-manipulation': 10
    };
    return topicMap[path] || 1;
}

async function toggleProblemStatus(problemIndex, topicId) {
    try {
        const response = await fetch("/update_progress", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question_id: problemIndex + 1,
                topic_id: topicId
            }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
            updateButtonStatus(problemIndex, true);
            loadStudentProgress();
            showNotification("Progress updated successfully!", "success");
        } else if (data.message === 'Question already completed!') {
            showNotification("You've already completed this question!", "info");
        } else {
            throw new Error(data.message || "Failed to save progress");
        }
    } catch (error) {
        console.error("Error saving progress:", error);
        showNotification("Failed to save progress. Please try again.", "error");
    }
}

async function loadStudentProgress() {
    try {
        const topicId = getCurrentTopicId();
        const response = await fetch(`/student_progress?topic_id=${topicId}`);
        if (!response.ok) throw new Error("Failed to load progress");

        const data = await response.json();
        if (data.completed_questions > 0) {
            for (let i = 0; i < data.completed_questions; i++) {
                updateButtonStatus(i, true);
            }
            updateProgressCount(data.completed_questions);
        }
    } catch (error) {
        console.error("Error loading progress:", error);
        showNotification("Failed to load progress", "error");
    }
}

function updateButtonStatus(index, completed) {
    const button = document.querySelectorAll("tbody tr")[index].querySelector("button");
    button.className = completed ? "btn btn-success btn-sm" : "btn btn-default btn-sm";
    button.innerHTML = completed ? "Completed" : "Mark Complete";
}

function updateProgressCount(completedCount) {
    const totalProblems = document.querySelectorAll("tbody tr").length;
    let progressDisplay = document.getElementById("progress-display") || document.createElement("div");
    progressDisplay.id = "progress-display";
    progressDisplay.className = "alert alert-info";
    progressDisplay.innerHTML = `Progress: ${completedCount}/${totalProblems} problems completed`;
    
    const content = document.querySelector(".content");
    if (content.firstChild) {
        content.insertBefore(progressDisplay, content.firstChild);
    } else {
        content.appendChild(progressDisplay);
    }
}

function showNotification(message, type = "info") {
    const notification = document.createElement("div");
    notification.className = `alert alert-${type} notification`;
    notification.style.position = "fixed";
    notification.style.top = "20px";
    notification.style.right = "20px";
    notification.style.zIndex = "1000";
    notification.innerHTML = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
} 