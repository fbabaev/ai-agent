const apiBase = "http://localhost:8000";

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
  console.log("DOM loaded, checking elements...");
  
  // Add a small delay to ensure everything is loaded
  setTimeout(function() {
    // Check if all required elements exist
    const fileInput = document.getElementById("fileInput");
    const questionInput = document.getElementById("question");
    const answerBox = document.getElementById("answer");
    const uploadBtn = document.getElementById("uploadBtn");
    const askBtn = document.getElementById("askBtn");
    
    console.log("File input:", fileInput);
    console.log("Question input:", questionInput);
    console.log("Answer box:", answerBox);
    console.log("Upload button:", uploadBtn);
    console.log("Ask button:", askBtn);
    
    if (!fileInput) {
      console.error("❌ fileInput element is missing!");
    }
    if (!questionInput) {
      console.error("❌ questionInput element is missing!");
    }
    if (!answerBox) {
      console.error("❌ answerBox element is missing!");
    }
    if (!uploadBtn) {
      console.error("❌ uploadBtn element is missing!");
    } else {
      uploadBtn.addEventListener('click', uploadFile);
    }
    if (!askBtn) {
      console.error("❌ askBtn element is missing!");
    } else {
      askBtn.addEventListener('click', askQuestion);
    }
    
    if (fileInput && questionInput && answerBox) {
      console.log("✅ All elements found successfully!");
    } else {
      console.error("❌ Some required elements are missing!");
    }
  }, 100);

  loadLibrary();
  setupDeleteModal();
});

async function uploadFile() {
  const input = document.getElementById("fileInput");
  const answerBox = document.getElementById("answer");

  // Check if elements exist
  if (!input) {
    console.error("File input element not found");
    return;
  }
  
  if (!answerBox) {
    console.error("Answer element not found");
    alert("Error: Answer display element not found");
    return;
  }

  if (!input.files.length) return alert("Please choose a file.");

  const formData = new FormData();
  formData.append("file", input.files[0]);

  try {
    answerBox.innerText = "Uploading...";
    const res = await fetch(`${apiBase}/upload`, {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.error || "Upload failed");
    }

    const data = await res.json();
    answerBox.innerText = `✅ ${data.status || `File uploaded: ${data.filename}`}`;
    loadLibrary();
  } catch (err) {
    console.error(err);
    answerBox.innerText = `❌ Upload failed: ${err.message}`;
  }
}

async function askQuestion() {
  const questionInput = document.getElementById("question");
  const answerBox = document.getElementById("answer");
  
  // Check if elements exist
  if (!questionInput) {
    console.error("Question input element not found");
    return;
  }
  
  if (!answerBox) {
    console.error("Answer element not found");
    alert("Error: Answer display element not found");
    return;
  }
  
  const question = questionInput.value;

  if (!question) return alert("Please ask a question.");

  try {
    answerBox.innerText = "Thinking...";
    const res = await fetch(`${apiBase}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.error || "Question failed");
    }

    const data = await res.json();
    answerBox.innerText = data.answer || "No answer returned.";
  } catch (err) {
    console.error(err);
    answerBox.innerText = `❌ Error: ${err.message}`;
  }
}

let editingFile = null;

function renderLibrary(files) {
  const libraryDiv = document.getElementById('library');
  libraryDiv.innerHTML = '';
  files.forEach(file => {
    const fileId = file.filename || file.name;
    const itemDiv = document.createElement('div');
    itemDiv.className = 'library-item';

    // Left: filename and timestamp in one line
    const leftDiv = document.createElement('div');
    leftDiv.className = 'library-left';

    if (editingFile === fileId) {
      // Edit mode: show input and Save/Cancel only
      const editRow = document.createElement('div');
      editRow.className = 'edit-row';
      editRow.style.display = '';
      editRow.style.alignItems = '';
      editRow.style.width = '';
      editRow.style.gap = '';
      editRow.style.flexWrap = '';
      editRow.style.maxWidth = '';

      const input = document.createElement('input');
      input.type = 'text';
      input.value = file.title || fileId;
      input.style.fontSize = '1em';
      input.style.flex = '1 1 0';
      input.style.padding = '0.35em 0.7em';
      input.style.borderRadius = '5px';
      input.style.border = '1.5px solid #bfc7d1';
      input.style.background = '#f8fafc';
      input.style.color = '#222';
      input.style.boxSizing = 'border-box';
      input.style.outline = 'none';
      input.style.transition = 'border 0.2s, box-shadow 0.2s';
      editRow.appendChild(input);

      // Actions: Save/Cancel only
      const actionsDiv = document.createElement('div');
      actionsDiv.className = 'library-actions';
      actionsDiv.style.marginLeft = '0';
      actionsDiv.style.gap = '0.7em';

      const saveBtn = document.createElement('button');
      saveBtn.className = 'library-btn edit';
      saveBtn.textContent = 'Save';
      saveBtn.onclick = async () => {
        const newTitle = input.value.trim();
        if (!newTitle) return alert('Title cannot be empty.');
        try {
          const res = await fetch(`${apiBase}/library/${encodeURIComponent(fileId)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
          });
          if (!res.ok) throw new Error('Update failed');
          editingFile = null;
          // Update the title in the UI without full reload
          file.title = newTitle;
          renderLibrary(window._lastFiles || []);
          showToast('Title updated!');
        } catch (err) {
          showToast('Update failed');
          loadLibrary();
        }
      };
      actionsDiv.appendChild(saveBtn);

      const cancelBtn = document.createElement('button');
      cancelBtn.className = 'library-btn cancel';
      cancelBtn.textContent = 'Cancel';
      cancelBtn.onclick = () => {
        editingFile = null;
        loadLibrary();
      };
      actionsDiv.appendChild(cancelBtn);

      editRow.appendChild(actionsDiv);
      itemDiv.appendChild(editRow);
    } else {
      // Normal mode
      const nameSpan = document.createElement('span');
      nameSpan.className = 'library-filename';
      nameSpan.textContent = file.title || fileId;
      leftDiv.appendChild(nameSpan);

      const tsSpan = document.createElement('span');
      tsSpan.className = 'library-timestamp';
      tsSpan.textContent = file.timestamp ? new Date(file.timestamp).toLocaleString() : '';
      leftDiv.appendChild(tsSpan);

      itemDiv.appendChild(leftDiv);

      // Actions: Edit/Delete
      const actionsDiv = document.createElement('div');
      actionsDiv.className = 'library-actions';

      const editBtn = document.createElement('button');
      editBtn.className = 'library-btn edit';
      editBtn.textContent = 'Edit';
      editBtn.onclick = (e) => {
        e.stopPropagation();
        // Only one edit at a time
        if (document.querySelector('.edit-row')) return;
        const originalHTML = itemDiv.innerHTML;
        itemDiv.innerHTML = '';
        const editRow = document.createElement('div');
        editRow.className = 'edit-row';
        const input = document.createElement('input');
        input.type = 'text';
        input.value = file.title || fileId;
        input.style.fontSize = '1em';
        input.style.flex = '1 1 0';
        input.style.padding = '0.35em 0.7em';
        input.style.borderRadius = '5px';
        input.style.border = '1.5px solid #bfc7d1';
        input.style.background = '#f8fafc';
        input.style.color = '#222';
        input.style.boxSizing = 'border-box';
        input.style.outline = 'none';
        input.style.transition = 'border 0.2s, box-shadow 0.2s';
        editRow.appendChild(input);
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'library-actions';
        actionsDiv.style.marginLeft = '0';
        actionsDiv.style.gap = '0.7em';
        const saveBtn = document.createElement('button');
        saveBtn.className = 'library-btn edit';
        saveBtn.textContent = 'Save';
        saveBtn.onclick = async () => {
          const newTitle = input.value.trim();
          if (!newTitle) return alert('Title cannot be empty.');
          try {
            const res = await fetch(`${apiBase}/library/${encodeURIComponent(fileId)}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ title: newTitle })
            });
            if (!res.ok) throw new Error('Update failed');
            file.title = newTitle;
            showToast('Title updated!');
            renderLibrary(window._lastFiles || []);
          } catch (err) {
            showToast('Update failed');
            renderLibrary(window._lastFiles || []);
          }
        };
        actionsDiv.appendChild(saveBtn);
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'library-btn cancel';
        cancelBtn.textContent = 'Cancel';
        cancelBtn.onclick = () => {
          itemDiv.innerHTML = originalHTML;
        };
        actionsDiv.appendChild(cancelBtn);
        editRow.appendChild(actionsDiv);
        itemDiv.appendChild(editRow);
        input.focus();
      };
      actionsDiv.appendChild(editBtn);

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'library-btn delete';
      deleteBtn.textContent = 'Delete';
      deleteBtn.onclick = (e) => {
        e.stopPropagation();
        showDeleteModal(fileId, itemDiv);
      };
      actionsDiv.appendChild(deleteBtn);

      itemDiv.appendChild(actionsDiv);
    }

    libraryDiv.appendChild(itemDiv);
  });
}

async function loadLibrary() {
  const libraryDiv = document.getElementById('library');
  if (!libraryDiv) {
    console.error('Library div not found!');
    return;
  }
  libraryDiv.innerHTML = '';
  try {
    const res = await fetch(`${apiBase}/library`);
    const files = await res.json();
    if (!Array.isArray(files) || files.length === 0) {
      libraryDiv.innerHTML = '<div style="color:#888; text-align:center;">No files uploaded yet.</div>';
      return;
    }
    window._lastFiles = files.slice().reverse();
    renderLibrary(files.slice().reverse());
  } catch (err) {
    libraryDiv.innerHTML = '<div style="color:#d9534f; text-align:center;">Failed to load library.</div>';
    console.error('Failed to load library:', err);
  }
}

async function updateTitle(filename, newTitle) {
  await fetch(`${apiBase}/library/${encodeURIComponent(filename)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: newTitle })
  });
  loadLibrary();
}

// Delete Modal Logic
let deleteFileName = null;
let deleteItemDiv = null;
function setupDeleteModal() {
  const modal = document.getElementById('deleteModal');
  const confirmBtn = document.getElementById('confirmDeleteBtn');
  const cancelBtn = document.getElementById('cancelDeleteBtn');
  if (!modal || !confirmBtn || !cancelBtn) return;
  confirmBtn.onclick = async function() {
    if (deleteFileName && deleteItemDiv) {
      confirmBtn.textContent = 'Deleting...';
      confirmBtn.disabled = true;
      try {
        const res = await fetch(`${apiBase}/library/${encodeURIComponent(deleteFileName)}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Delete failed');
        deleteItemDiv.classList.add('removing');
        setTimeout(() => {
          if (deleteItemDiv) {
            deleteItemDiv.remove();
            deleteItemDiv = null;
          }
          showToast('File deleted!');
          loadLibrary();
        }, 400);
      } catch (err) {
        showToast('Delete failed');
        loadLibrary();
      }
      confirmBtn.textContent = 'Delete';
      confirmBtn.disabled = false;
    }
    modal.style.display = 'none';
    deleteFileName = null;
    deleteItemDiv = null;
  };
  cancelBtn.onclick = function() {
    modal.style.display = 'none';
    deleteFileName = null;
    deleteItemDiv = null;
  };
}
function showDeleteModal(filename, itemDiv) {
  deleteFileName = filename;
  deleteItemDiv = itemDiv;
  const modal = document.getElementById('deleteModal');
  modal.style.display = 'flex';
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.className = 'show';
  setTimeout(() => { toast.className = toast.className.replace('show', ''); }, 2000);
}

window.loadLibrary = loadLibrary;