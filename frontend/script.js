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
    
    console.log("File input:", fileInput);
    console.log("Question input:", questionInput);
    console.log("Answer box:", answerBox);
    
    if (!fileInput) {
      console.error("❌ fileInput element is missing!");
    }
    if (!questionInput) {
      console.error("❌ questionInput element is missing!");
    }
    if (!answerBox) {
      console.error("❌ answerBox element is missing!");
    }
    
    if (fileInput && questionInput && answerBox) {
      console.log("✅ All elements found successfully!");
    } else {
      console.error("❌ Some required elements are missing!");
    }
  }, 100);
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