document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-rename-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const row = button.closest(".session-item-row");
            const form = row ? row.querySelector(".session-rename-form") : null;
            const input = form ? form.querySelector("input[name=title]") : null;
            if (!form) {
                return;
            }
            form.hidden = !form.hidden;
            if (!form.hidden && input) {
                input.focus();
                input.select();
            }
        });
    });

    document.querySelectorAll("[data-confirm-delete]").forEach((button) => {
        button.addEventListener("click", (event) => {
            if (!window.confirm("Delete this chat session?")) {
                event.preventDefault();
            }
        });
    });

    const fileInput = document.getElementById("fileInput");
    const attachButton = document.getElementById("attachBtn");
    const selectedFile = document.getElementById("stagedFile");
    const selectedFileName = document.getElementById("stagedFileName");
    const removeFile = document.getElementById("removeFileBtn");
    const messageInput = document.getElementById("messageInput");
    const chatForm = document.getElementById("chatForm");
    const chatScroll = document.getElementById("chatScroll");
    const dropZone = document.getElementById("dropZone");

    if (!chatForm || !messageInput || !chatScroll) {
        return;
    }

    function csrfToken() {
        const field = chatForm.querySelector("[name=csrfmiddlewaretoken]");
        if (field && field.value) {
            return field.value;
        }
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function stageFile(file) {
        if (!file) {
            return;
        }

        const transfer = new DataTransfer();
        transfer.items.add(file);
        fileInput.files = transfer.files;
        selectedFileName.textContent = file.name;
        selectedFile.style.display = "flex";
    }

    attachButton.addEventListener("click", () => {
        fileInput.click();
    });

    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (!file) {
            return;
        }
        stageFile(file);
    });

    removeFile.addEventListener("click", () => {
        fileInput.value = "";
        selectedFile.style.display = "none";
    });

    if (dropZone) {
        ["dragenter", "dragover"].forEach((eventName) => {
            dropZone.addEventListener(eventName, (event) => {
                event.preventDefault();
                dropZone.classList.add("is-dragover");
            });
        });

        ["dragleave", "drop"].forEach((eventName) => {
            dropZone.addEventListener(eventName, (event) => {
                event.preventDefault();
                dropZone.classList.remove("is-dragover");
            });
        });

        dropZone.addEventListener("drop", (event) => {
            const file = event.dataTransfer.files[0];
            if (file) {
                stageFile(file);
                messageInput.focus();
            }
        });
    }

    messageInput.addEventListener("input", () => {
        messageInput.style.height = "auto";
        messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + "px";
    });

    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.requestSubmit();
        }
    });

    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const text = messageInput.value.trim();
        const file = fileInput.files[0];

        if (!text && !file) {
            return;
        }

        appendUserMessage(text, file ? file.name : null);

        const formData = new FormData(chatForm);
        const typingEl = appendTyping();

        chatForm.reset();
        messageInput.style.height = "auto";
        fileInput.value = "";
        selectedFile.style.display = "none";

        try {
            const response = await fetch(chatForm.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-CSRFToken": csrfToken(),
                },
            });

            const data = await response.json();
            typingEl.remove();
            appendAssistantMessage(data);
        } catch (err) {
            typingEl.remove();
            appendAssistantMessage({
                text: "Something went wrong sending that — try again.",
                finding: null,
            });
            console.error(err);
        }
    });

    function appendUserMessage(text, fileName) {
        const el = document.createElement("div");
        el.className = "msg user";
        const body = document.createElement("div");
        body.className = "msg-body";

        const avatar = document.createElement("div");
        avatar.className = "msg-avatar";
        avatar.textContent = "You";

        if (fileName) {
            const thumb = document.createElement("div");
            thumb.className = "attach-thumb";
            const icon = document.createElement("span");
            icon.className = "filetype-icon";
            icon.textContent = "FILE";
            const name = document.createElement("span");
            name.textContent = fileName;
            thumb.append(icon, name);
            body.appendChild(thumb);
        }

        if (text) {
            const bubble = document.createElement("div");
            bubble.className = "msg-bubble";
            bubble.textContent = text;
            body.appendChild(bubble);
        }

        const time = document.createElement("div");
        time.className = "msg-time";
        time.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        body.appendChild(time);

        el.append(avatar, body);
        chatScroll.appendChild(el);
        chatScroll.scrollTop = chatScroll.scrollHeight;
    }

    function appendTyping() {
        const el = document.createElement("div");
        el.className = "msg assistant";
        el.innerHTML = `<div class="msg-avatar">GM</div><div class="msg-body">
            <div class="typing-row"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>
        </div>`;
        chatScroll.appendChild(el);
        chatScroll.scrollTop = chatScroll.scrollHeight;
        return el;
    }

    function appendAssistantMessage(data) {
        const el = document.createElement("div");
        el.className = "msg assistant";

        const avatar = document.createElement("div");
        avatar.className = "msg-avatar";
        avatar.textContent = "GM";

        const body = document.createElement("div");
        body.className = "msg-body";

        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";
        bubble.textContent = data.text || "";
        body.appendChild(bubble);

        if (data.finding) {
            const card = document.createElement("div");
            card.className = "finding-card severity-" + (data.finding.severity || "advisory");

            const head = document.createElement("div");
            head.className = "finding-head";
            const chip = document.createElement("span");
            chip.className = "severity-chip";
            chip.textContent = data.finding.severity || "";
            const conf = document.createElement("span");
            conf.className = "confidence";
            conf.textContent = (data.finding.confidence ?? "") + "% confidence";
            head.append(chip, conf);

            const title = document.createElement("div");
            title.className = "finding-title";
            title.textContent = data.finding.title || "";
            const fbody = document.createElement("div");
            fbody.className = "finding-body";
            fbody.textContent = data.finding.body || "";
            const rec = document.createElement("div");
            rec.className = "finding-rec";
            const rk = document.createElement("span");
            rk.className = "rk";
            rk.textContent = "Next: ";
            rec.append(rk, document.createTextNode(data.finding.recommendation || ""));

            card.append(head, title, fbody, rec);
            body.appendChild(card);
        }

        const time = document.createElement("div");
        time.className = "msg-time";
        time.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        body.appendChild(time);

        el.append(avatar, body);
        chatScroll.appendChild(el);
        chatScroll.scrollTop = chatScroll.scrollHeight;
    }

    chatScroll.scrollTop = chatScroll.scrollHeight;
});
