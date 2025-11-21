document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const resetBtn = document.getElementById('reset-btn');
    
    // Drag and Drop Events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        uploadArea.classList.add('dragover');
    }

    function unhighlight(e) {
        uploadArea.classList.remove('dragover');
    }

    uploadArea.addEventListener('drop', handleDrop, false);
    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFiles);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles({ target: { files: files } });
    }

    function handleFiles(e) {
        const files = e.target.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    }

    function uploadFile(file) {
        if (file.type !== 'application/pdf') {
            alert('Please upload a PDF file.');
            return;
        }

        // UI Transition
        uploadArea.classList.add('hidden');
        loading.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file', file);

        fetch('/analyze', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                resetUI();
            } else {
                showResults(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred during analysis.');
            resetUI();
        });
    }

    function showResults(data) {
        loading.classList.add('hidden');
        results.classList.remove('hidden');

        // Animate Score
        const scoreValue = document.getElementById('score-value');
        const scoreProgress = document.getElementById('score-progress');
        const score = data.score;
        
        // Calculate stroke-dashoffset (440 is circumference for r=70)
        const offset = 440 - (440 * score) / 100;
        
        // Reset animation
        scoreProgress.style.strokeDashoffset = 440;
        
        // Trigger animation after a small delay
        setTimeout(() => {
            scoreProgress.style.strokeDashoffset = offset;
            animateValue(scoreValue, 0, score, 1500);
        }, 100);

        // Render Skills
        const skillsList = document.getElementById('skills-list');
        skillsList.innerHTML = '';
        if (data.skills.length > 0) {
            data.skills.forEach(skill => {
                const tag = document.createElement('span');
                tag.className = 'tag';
                tag.textContent = skill;
                skillsList.appendChild(tag);
            });
        } else {
            skillsList.innerHTML = '<span class="tag">No specific skills detected</span>';
        }

        // Render Feedback
        const feedbackList = document.getElementById('feedback-list');
        feedbackList.innerHTML = '';
        data.feedback.forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            feedbackList.appendChild(li);
        });
    }

    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    resetBtn.addEventListener('click', resetUI);

    function resetUI() {
        results.classList.add('hidden');
        loading.classList.add('hidden');
        uploadArea.classList.remove('hidden');
        fileInput.value = '';
    }
});
