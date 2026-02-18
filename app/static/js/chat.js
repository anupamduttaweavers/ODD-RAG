"use strict";

// ==========================================================
//  Particle constellation background
// ==========================================================

(function () {
    var canvas = document.getElementById("particleCanvas");
    var ctx = canvas.getContext("2d");
    var particles = [];
    var PARTICLE_COUNT = 90;
    var CONNECT_DISTANCE = 140;
    var mouse = { x: null, y: null };
    var animId = null;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    window.addEventListener("resize", resize);
    resize();

    function Particle() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.vx = (Math.random() - 0.5) * 0.4;
        this.vy = (Math.random() - 0.5) * 0.4;
        this.radius = Math.random() * 1.8 + 0.6;
        this.baseAlpha = Math.random() * 0.5 + 0.3;
        this.alpha = this.baseAlpha;
        this.pulseSpeed = Math.random() * 0.01 + 0.005;
        this.pulseOffset = Math.random() * Math.PI * 2;
    }

    Particle.prototype.update = function (time) {
        this.x += this.vx;
        this.y += this.vy;

        // Wrap around edges
        if (this.x < 0) this.x = canvas.width;
        if (this.x > canvas.width) this.x = 0;
        if (this.y < 0) this.y = canvas.height;
        if (this.y > canvas.height) this.y = 0;

        // Gentle pulse
        this.alpha = this.baseAlpha + Math.sin(time * this.pulseSpeed + this.pulseOffset) * 0.15;
    };

    Particle.prototype.draw = function () {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255, 255, 255, " + this.alpha + ")";
        ctx.fill();
    };

    function init() {
        particles = [];
        for (var i = 0; i < PARTICLE_COUNT; i++) {
            particles.push(new Particle());
        }
    }

    function connectParticles() {
        for (var i = 0; i < particles.length; i++) {
            for (var j = i + 1; j < particles.length; j++) {
                var dx = particles[i].x - particles[j].x;
                var dy = particles[i].y - particles[j].y;
                var dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < CONNECT_DISTANCE) {
                    var opacity = (1 - dist / CONNECT_DISTANCE) * 0.2;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = "rgba(255, 255, 255, " + opacity + ")";
                    ctx.lineWidth = 0.6;
                    ctx.stroke();
                }
            }

            // Connect to mouse cursor when nearby
            if (mouse.x !== null) {
                var mdx = particles[i].x - mouse.x;
                var mdy = particles[i].y - mouse.y;
                var mDist = Math.sqrt(mdx * mdx + mdy * mdy);
                if (mDist < CONNECT_DISTANCE * 1.5) {
                    var mOpacity = (1 - mDist / (CONNECT_DISTANCE * 1.5)) * 0.35;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(mouse.x, mouse.y);
                    ctx.strokeStyle = "rgba(180, 200, 255, " + mOpacity + ")";
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }
    }

    function animate(time) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        for (var i = 0; i < particles.length; i++) {
            particles[i].update(time);
            particles[i].draw();
        }
        connectParticles();
        animId = requestAnimationFrame(animate);
    }

    document.addEventListener("mousemove", function (e) {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });

    document.addEventListener("mouseleave", function () {
        mouse.x = null;
        mouse.y = null;
    });

    init();
    animate(0);
})();


// ==========================================================
//  Chat logic
// ==========================================================

var messagesContainer = document.getElementById("messagesContainer");
var messageInput = document.getElementById("messageInput");
var sendButton = document.getElementById("sendButton");
var hasMessages = false;

// Auto-resize textarea
messageInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 80) + "px";
});

// Send message on Enter (Ctrl+Enter / Shift+Enter for new line)
messageInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter" && !e.ctrlKey && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

function clearEmptyState() {
    if (!hasMessages) {
        messagesContainer.innerHTML = "";
        hasMessages = true;
    }
}

function addMessage(text, isUser) {
    clearEmptyState();

    var messageDiv = document.createElement("div");
    messageDiv.className = "message " + (isUser ? "user" : "bot");

    var contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.textContent = text;

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addLoadingIndicator() {
    clearEmptyState();

    var messageDiv = document.createElement("div");
    messageDiv.className = "message bot";
    messageDiv.id = "loadingMessage";

    var contentDiv = document.createElement("div");
    contentDiv.className = "loading-indicator";
    contentDiv.innerHTML =
        '<span>Thinking</span>' +
        '<span class="loading-dot"></span>' +
        '<span class="loading-dot"></span>' +
        '<span class="loading-dot"></span>';

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function removeLoadingIndicator() {
    var loadingMessage = document.getElementById("loadingMessage");
    if (loadingMessage) {
        loadingMessage.remove();
    }
}

async function sendMessage() {
    var message = messageInput.value.trim();
    if (!message) return;

    addMessage(message, true);

    messageInput.value = "";
    messageInput.style.height = "auto";
    messageInput.disabled = true;
    sendButton.disabled = true;

    addLoadingIndicator();

    try {
        var response = await fetch("/api/v1/chatbot/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: message }),
        });

        removeLoadingIndicator();

        if (!response.ok) {
            throw new Error("HTTP error! status: " + response.status);
        }

        var data = await response.json();
        var answer = data.answer || "Sorry, I could not process your request.";
        addMessage(answer, false);
    } catch (error) {
        removeLoadingIndicator();
        console.error("Error:", error);
        addMessage("Sorry, there was an error processing your request. Please try again.", false);
    } finally {
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

messageInput.focus();
