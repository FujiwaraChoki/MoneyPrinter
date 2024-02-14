const videoSubject = document.querySelector("#videoSubject");
const aiModel = document.querySelector("#aiModel");
const voice = document.querySelector("#voice");
const zipUrl = document.querySelector("#zipUrl");
const paragraphNumber = document.querySelector("#paragraphNumber");
const youtubeToggle = document.querySelector("#youtubeUploadToggle");
const useMusicToggle = document.querySelector("#useMusicToggle");
const customPrompt = document.querySelector("#customPrompt");
const generateButton = document.querySelector("#generateButton");
const cancelButton = document.querySelector("#cancelButton");

const advancedOptionsToggle = document.querySelector("#advancedOptionsToggle");

advancedOptionsToggle.addEventListener("click", () => {
  // Change Emoji, from ▼ to ▲ and vice versa
  const emoji = advancedOptionsToggle.textContent;
  advancedOptionsToggle.textContent = emoji.includes("▼")
    ? "Show less Options ▲"
    : "Show Advanced Options ▼";
  const advancedOptions = document.querySelector("#advancedOptions");
  advancedOptions.classList.toggle("hidden");
});


const cancelGeneration = () => {
  console.log("Canceling generation...");
  // Send request to /cancel
  fetch("http://localhost:8080/api/cancel", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      alert(data.message);
      console.log(data);
    })
    .catch((error) => {
      alert("An error occurred. Please try again later.");
      console.log(error);
    });

  // Hide cancel button
  cancelButton.classList.add("hidden");

  // Enable generate button
  generateButton.disabled = false;
  generateButton.classList.remove("hidden");
};

const generateVideo = () => {
  console.log("Generating video...");
  // Disable button and change text
  generateButton.disabled = true;
  generateButton.classList.add("hidden");

  // Show cancel button
  cancelButton.classList.remove("hidden");

  // Get values from input fields
  const videoSubjectValue = videoSubject.value;
  const aiModelValue = aiModel.value;
  const voiceValue = voice.value;
  const paragraphNumberValue = paragraphNumber.value;
  const youtubeUpload = youtubeToggle.checked;
  const useMusicToggleState = useMusicToggle.checked;
  const threads = document.querySelector("#threads").value;
  const zipUrlValue = zipUrl.value;
  const customPromptValue = customPrompt.value;
  const subtitlesPosition = document.querySelector("#subtitlesPosition").value;
  const colorHexCode = document.querySelector("#subtitlesColor").value;


  const url = "http://localhost:8080/api/generate";

  // Construct data to be sent to the server
  const data = {
    videoSubject: videoSubjectValue,
    aiModel: aiModelValue,
    voice: voiceValue,
    paragraphNumber: paragraphNumberValue,
    automateYoutubeUpload: youtubeUpload,
    useMusic: useMusicToggleState,
    zipUrl: zipUrlValue,
    threads: threads,
    subtitlesPosition: subtitlesPosition,
    customPrompt: customPromptValue,
    color: colorHexCode,
  };

  // Send the actual request to the server
  fetch(url, {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      alert(data.message);
      // Hide cancel button after generation is complete
      generateButton.disabled = false;
      generateButton.classList.remove("hidden");
      cancelButton.classList.add("hidden");
    })
    .catch((error) => {
      alert("An error occurred. Please try again later.");
      console.log(error);
    });
};

generateButton.addEventListener("click", generateVideo);
cancelButton.addEventListener("click", cancelGeneration);

videoSubject.addEventListener("keyup", (event) => {
  if (event.key === "Enter") {
    generateVideo();
  }
});

// Load the data from localStorage on page load
document.addEventListener("DOMContentLoaded", (event) => {
  const voiceSelect = document.getElementById("voice");
  const storedVoiceValue = localStorage.getItem("voiceValue");

  if (storedVoiceValue) {
    voiceSelect.value = storedVoiceValue;
  }
});

// Save the data to localStorage when the user changes the value
toggles = ["youtubeUploadToggle", "useMusicToggle", "reuseChoicesToggle"];
fields = ["aiModel", "voice", "paragraphNumber", "videoSubject", "zipUrl", "customPrompt", "threads", "subtitlesPosition", "subtitlesColor"];

document.addEventListener("DOMContentLoaded", () => {
  toggles.forEach((id) => {
    const toggle = document.getElementById(id);
    const storedValue = localStorage.getItem(`${id}Value`);
    const storedReuseValue = localStorage.getItem("reuseChoicesToggleValue");

    if (toggle && storedValue !== null && storedReuseValue === "true") {
        toggle.checked = storedValue === "true";
    }
    // Attach change listener to update localStorage
    toggle.addEventListener("change", (event) => {
        localStorage.setItem(`${id}Value`, event.target.checked);
    });
  });

  fields.forEach((id) => {
    const select = document.getElementById(id);
    const storedValue = localStorage.getItem(`${id}Value`);
    const storedReuseValue = localStorage.getItem("reuseChoicesToggleValue");

    if (storedValue && storedReuseValue === "true") {
      select.value = storedValue;
    }
    // Attach change listener to update localStorage
    select.addEventListener("change", (event) => {
      localStorage.setItem(`${id}Value`, event.target.value);
    });
  });
});
