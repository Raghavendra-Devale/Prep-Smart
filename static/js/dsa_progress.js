// Progress tracking functionality for DSA topics
document.addEventListener("DOMContentLoaded", function () {
    initializeProgress();
});

function initializeProgress() {
    const rows = document.querySelectorAll("tbody tr");
    const totalProblems = rows.length;

    rows.forEach((row, index) => {
        // Create button cell if it doesn't exist
        if (!row.querySelector('.status-btn')) {
            const buttonCell = document.createElement("td");
            const button = document.createElement("button");
            button.className = "btn btn-default btn-sm status-btn";
            button.innerHTML = "Mark Complete";
            button.onclick = function () {
                toggleProblemStatus(index + 1, getCurrentTopicId());
            };

            buttonCell.appendChild(button);
            row.appendChild(buttonCell);
        }
    });

    // Create progress display
    let progressDisplay = document.getElementById("progress-display");
    if (!progressDisplay) {
        progressDisplay = document.createElement("div");
        progressDisplay.id = "progress-display";
        progressDisplay.className = "alert alert-info";
        document.querySelector(".content").prepend(progressDisplay);
    }

    // Load saved progress
    loadStudentProgress();
}

function getCurrentTopicId() {
    // Extract topic ID from URL
    const path = window.location.pathname;
    console.log("Current path:", path); // Debug log
    
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

    // Normalize path by removing trailing slash if present
    const normalizedPath = path.endsWith('/') ? path.slice(0, -1) : path;
    console.log("Normalized path:", normalizedPath); // Debug log
    
    const topicId = topicMap[normalizedPath];
    console.log("Topic ID:", topicId); // Debug log
    
    if (!topicId) {
        console.warn(`No topic ID found for path: ${normalizedPath}`);
    }
    
    return topicId || 1; // Default to 1 if not found
}

async function toggleProblemStatus(questionId, topicId) {
    try {
        console.log(`Updating progress - Question: ${questionId}, Topic: ${topicId}`); // Debug log
        
        const response = await fetch("/update_progress", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question_id: questionId,
                topic_id: topicId
            }),
        });

        const data = await response.json();
        console.log("Server response:", data); // Debug log

        if (response.ok && data.success) {
            updateProgressDisplay({
                topic_progress: data.topic_progress,
                total_topic_questions: data.total_topic_questions,
                dsa_progress: data.dsa_progress,
                total_dsa_questions: data.total_dsa_questions
            });
            updateButtonStatus(questionId - 1, true);
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
        console.log(`Loading progress for topic ID: ${topicId}`); // Debug log
        
        const response = await fetch(`/student_progress?topic_id=${topicId}`);
        if (!response.ok) throw new Error("Failed to load progress");

        const data = await response.json();
        console.log("Loaded progress data:", data); // Debug log
        
        if (data.success) {
            updateProgressDisplay({
                topic_progress: data.completed_questions,
                total_topic_questions: getTotalQuestions(),
                dsa_progress: data.dsa_completed,
                total_dsa_questions: data.dsa_total
            });

            // Mark completed questions
            const completedCount = data.completed_questions;
            const buttons = document.querySelectorAll('.status-btn');
            console.log(`Marking ${completedCount} questions as completed`); // Debug log
            
            for (let i = 0; i < buttons.length; i++) {
                if (i < completedCount) {
                    updateButtonStatus(i, true);
                }
            }
        }
    } catch (error) {
        console.error("Error loading progress:", error);
        showNotification("Failed to load progress", "error");
    }
}

function getTotalQuestions() {
    const total = document.querySelectorAll("tbody tr").length;
    console.log(`Total questions in current topic: ${total}`); // Debug log
    return total;
}

function updateProgressDisplay(data) {
    const progressDisplay = document.getElementById("progress-display");
    if (progressDisplay) {
        const topicProgress = `Topic Progress: ${data.topic_progress}/${data.total_topic_questions} questions completed`;
        const dsaProgress = `Overall DSA Progress: ${data.dsa_progress}/${data.total_dsa_questions} total questions completed`;
        progressDisplay.innerHTML = `${topicProgress}<br>${dsaProgress}`;
        console.log("Updated progress display:", { topicProgress, dsaProgress }); // Debug log
    }
}

function updateButtonStatus(index, completed) {
    const button = document.querySelectorAll('.status-btn')[index];
    if (button) {
        button.className = completed ? "btn btn-success btn-sm status-btn" : "btn btn-default btn-sm status-btn";
        button.innerHTML = completed ? "Completed" : "Mark Complete";
        button.disabled = completed;
        console.log(`Updated button ${index} status to ${completed ? 'completed' : 'incomplete'}`); // Debug log
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
    console.log(`Showing notification: ${message} (${type})`); // Debug log

    setTimeout(() => {
        notification.remove();
    }, 3000);
} 