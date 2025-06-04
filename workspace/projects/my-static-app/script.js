function showMessage() {
    // Create message element if it doesn't exist
    let messageEl = document.querySelector('.message');
    if (!messageEl) {
        messageEl = document.createElement('div');
        messageEl.className = 'message';
        messageEl.innerHTML = '🎉 Hello from your deployed static app! This JavaScript is working perfectly.';

        // Insert after the button
        const button = document.querySelector('button');
        button.parentNode.insertBefore(messageEl, button.nextSibling);
    }

    // Show the message with animation
    messageEl.classList.add('show');

    // Hide after 3 seconds
    setTimeout(() => {
        messageEl.classList.remove('show');
    }, 3000);
}

// Add some interactive features when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Static app loaded successfully!');
    console.log('📦 Deployed via ConfigMap pattern');
    console.log('⚡ Served by NGINX in Kubernetes');

    // Add click counter
    let clickCount = 0;
    const button = document.querySelector('button');
    const originalText = button.textContent;

    button.addEventListener('click', function() {
        clickCount++;
        if (clickCount > 1) {
            button.textContent = `Clicked ${clickCount} times!`;
        }
    });

    // Reset button text after 5 seconds
    setInterval(() => {
        if (clickCount > 0) {
            button.textContent = originalText;
            clickCount = 0;
        }
    }, 5000);
});
