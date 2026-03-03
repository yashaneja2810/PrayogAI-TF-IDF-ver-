// Enhanced embeddable chatbot widget with dark mode, draggable, and resizable features
(function () {
  // Find script tag
  var script = document.currentScript || (function() {
    var scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();
  var botId = script.getAttribute('data-bot-id') || '';
  var companyName = script.getAttribute('data-company-name') || 'AI Assistant';
  var widgetColor = script.getAttribute('data-color') || '#2563eb';

  // Theme support
  var isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
  var themeConfig = {
    light: {
      background: '#ffffff',
      text: '#1a1a1a',
      messageBackground: '#f1f5f9',
      border: '#e5e7eb'
    },
    dark: {
      background: '#1a1a1a',
      text: '#ffffff',
      messageBackground: '#2d2d2d',
      border: '#404040'
    }
  };

  // Size configuration
  var sizes = {
    small: { width: '300px', height: '400px' },
    medium: { width: '340px', height: '480px' },
    large: { width: '380px', height: '560px' }
  };
  var currentSize = 'medium';

  // Create floating button
  var btn = document.createElement('div');
  btn.style.position = 'fixed';
  btn.style.bottom = '24px';
  btn.style.right = '24px';
  btn.style.width = '56px';
  btn.style.height = '56px';
  btn.style.background = widgetColor;
  btn.style.borderRadius = '50%';
  btn.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
  btn.style.display = 'flex';
  btn.style.alignItems = 'center';
  btn.style.justifyContent = 'center';
  btn.style.cursor = 'pointer';
  btn.style.zIndex = 9999;
  btn.innerHTML = '<svg width="28" height="28" fill="#fff" viewBox="0 0 24 24"><path d="M12 3C7.03 3 3 6.58 3 11c0 1.61.62 3.09 1.69 4.34-.13.5-.5 1.84-.7 2.56-.11.36.24.68.59.57.76-.25 2.12-.7 2.62-.86C8.7 18.47 10.28 19 12 19c4.97 0 9-3.58 9-8s-4.03-8-9-8zm-2 7h4v2h-4v-2zm8 0h-2v2h2v-2zm-8 4h4v2h-4v-2zm8 0h-2v2h2v-2z"/></svg>';

  // Create chat window
  var chat = document.createElement('div');
  chat.style.position = 'fixed';
  chat.style.bottom = '90px';
  chat.style.right = '24px';
  chat.style.width = '340px';
  chat.style.height = '420px';
  chat.style.background = '#fff';
  chat.style.borderRadius = '12px';
  chat.style.boxShadow = '0 4px 24px rgba(0,0,0,0.18)';
  chat.style.display = 'none';
  chat.style.flexDirection = 'column';
  chat.style.overflow = 'hidden';
  chat.style.zIndex = 9999;

  // Make chat window draggable
  var isDragging = false;
  var currentX;
  var currentY;
  var initialX;
  var initialY;
  var xOffset = 0;
  var yOffset = 0;

  // Chat header with controls
  var header = document.createElement('div');
  header.style.background = widgetColor;
  header.style.color = '#fff';
  header.style.padding = '12px 16px';
  header.style.display = 'flex';
  header.style.justifyContent = 'space-between';
  header.style.alignItems = 'center';
  header.style.cursor = 'move';
  
  // Company name and controls
  var title = document.createElement('div');
  title.style.fontWeight = 'bold';
  title.innerText = companyName;
  
  var controls = document.createElement('div');
  controls.style.display = 'flex';
  controls.style.gap = '8px';
  
  // Theme toggle
  var themeBtn = document.createElement('button');
  themeBtn.innerHTML = '🌓';
  themeBtn.style.background = 'none';
  themeBtn.style.border = 'none';
  themeBtn.style.color = '#fff';
  themeBtn.style.cursor = 'pointer';
  themeBtn.title = 'Toggle theme';
  
  // Size toggle
  var sizeBtn = document.createElement('button');
  sizeBtn.innerHTML = '⛶';
  sizeBtn.style.background = 'none';
  sizeBtn.style.border = 'none';
  sizeBtn.style.color = '#fff';
  sizeBtn.style.cursor = 'pointer';
  sizeBtn.title = 'Change size';
  
  controls.appendChild(themeBtn);
  controls.appendChild(sizeBtn);
  
  header.appendChild(title);
  header.appendChild(controls);
  chat.appendChild(header);

  // Chat messages
  var messages = document.createElement('div');
  messages.style.flex = '1';
  messages.style.padding = '12px';
  messages.style.overflowY = 'auto';
  chat.appendChild(messages);

  // Chat input
  var inputWrap = document.createElement('div');
  inputWrap.style.display = 'flex';
  inputWrap.style.borderTop = '1px solid #eee';
  var input = document.createElement('input');
  input.type = 'text';
  input.placeholder = 'Type your message...';
  input.style.flex = '1';
  input.style.padding = '10px';
  input.style.border = 'none';
  input.style.outline = 'none';
  var sendBtn = document.createElement('button');
  sendBtn.innerText = 'Send';
  sendBtn.style.background = widgetColor;
  sendBtn.style.color = '#fff';
  sendBtn.style.border = 'none';
  sendBtn.style.padding = '0 16px';
  sendBtn.style.cursor = 'pointer';
  inputWrap.appendChild(input);
  inputWrap.appendChild(sendBtn);
  chat.appendChild(inputWrap);

  // Toggle chat
  btn.onclick = function () {
    chat.style.display = chat.style.display === 'none' ? 'flex' : 'none';
  };

  // Theme toggle function
  function toggleTheme() {
    isDarkMode = !isDarkMode;
    const theme = isDarkMode ? themeConfig.dark : themeConfig.light;
    chat.style.background = theme.background;
    messages.style.background = theme.background;
    input.style.background = theme.background;
    input.style.color = theme.text;
    inputWrap.style.borderTop = '1px solid ' + theme.border;
    // Update existing messages
    messages.querySelectorAll('.message-bubble').forEach(bubble => {
      if (bubble.classList.contains('bot-message')) {
        bubble.style.background = theme.messageBackground;
        bubble.style.color = theme.text;
      }
    });
  }

  // Size toggle function
  function toggleSize() {
    const sizeOrder = ['small', 'medium', 'large'];
    const currentIndex = sizeOrder.indexOf(currentSize);
    currentSize = sizeOrder[(currentIndex + 1) % sizeOrder.length];
    const newSize = sizes[currentSize];
    chat.style.width = newSize.width;
    chat.style.height = newSize.height;
  }

  // Format bot response with markdown-like syntax
  function formatBotResponse(text) {
    // Convert **bold** to styled text
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Convert bullet points
    text = text.replace(/^- (.*)/gm, '• $1');
    // Convert numbered lists
    text = text.replace(/^\d+\. (.*)/gm, function(match) {
      return '  ' + match;  // Add indentation to numbered lists
    });
    return text;
  }

  // Send message
  function addMessage(text, from) {
    var msg = document.createElement('div');
    msg.style.margin = '8px 0';
    msg.style.textAlign = from === 'user' ? 'right' : 'left';
    
    var bubble = document.createElement('span');
    bubble.className = 'message-bubble ' + (from === 'user' ? 'user-message' : 'bot-message');
    bubble.style.display = 'inline-block';
    bubble.style.maxWidth = '80%';
    bubble.style.padding = '8px 12px';
    bubble.style.borderRadius = '8px';
    bubble.style.background = from === 'user' ? widgetColor : (isDarkMode ? themeConfig.dark.messageBackground : themeConfig.light.messageBackground);
    bubble.style.color = from === 'user' ? '#fff' : (isDarkMode ? themeConfig.dark.text : themeConfig.light.text);
    bubble.style.whiteSpace = 'pre-wrap';
    bubble.innerHTML = from === 'user' ? text : formatBotResponse(text);
    
    msg.appendChild(bubble);
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  }

  function sendMessage() {
    var text = input.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    input.value = '';
    // Call backend (updated to /api/chat)
    fetch('http://localhost:8000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bot_id: botId, query: text })
    })
      .then(r => r.json())
      .then(data => {
        if (data && data.response) {
          addMessage(data.response, 'bot');
        } else {
          addMessage('No response from bot.', 'bot');
        }
      })
      .catch(() => addMessage('Error contacting bot.', 'bot'));
  }
  // Draggable functionality
  function dragStart(e) {
    if (e.target === header) {
      initialX = e.clientX - xOffset;
      initialY = e.clientY - yOffset;
      isDragging = true;
    }
  }

  function dragEnd() {
    isDragging = false;
  }

  function drag(e) {
    if (isDragging) {
      e.preventDefault();
      currentX = e.clientX - initialX;
      currentY = e.clientY - initialY;
      xOffset = currentX;
      yOffset = currentY;
      chat.style.transform = `translate(${currentX}px, ${currentY}px)`;
    }
  }

  // Event listeners
  sendBtn.onclick = sendMessage;
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') sendMessage();
  });
  
  themeBtn.onclick = toggleTheme;
  sizeBtn.onclick = toggleSize;
  
  header.addEventListener('mousedown', dragStart);
  document.addEventListener('mousemove', drag);
  document.addEventListener('mouseup', dragEnd);

  // Initial theme
  if (isDarkMode) {
    toggleTheme();
  }

  // Add to page
  document.body.appendChild(btn);
  document.body.appendChild(chat);
})();
