// Use window.onload to ensure the DOM is fully loaded before running script
window.onload = function () {
  // --- DOM Elements ---
  const pupil = document.getElementById("camera-pupil");
  const lens = pupil.parentElement;
  const viewTitle = document.getElementById("view-title");
  const viewSubtitle = document.getElementById("view-subtitle");

  // ⚡️ FIX: Define Video and Canvas elements here ⚡️
  const video = document.getElementById('webcam-stream');
  const canvas = document.getElementById('image-canvas');
  const context = canvas ? canvas.getContext('2d') : null;

  // Form Inputs
  const loginUsernameInput = document.getElementById("login-username");
  const loginPasswordInput = document.getElementById("login-password");
  const signupEmailInput = document.getElementById("signup-email");
  // ⚡️ ADDED: New Username Input Element ⚡️
  const signupUsernameInput = document.getElementById("signup-username");
  const signupPasswordInput = document.getElementById("signup-password");
  const forgotEmailInput = document.getElementById("forgot-email");

  // Form Action Buttons (using a simple text selector for demonstration)
  const loginButton = document.querySelector(
    '#login-view button:not([class*="bg-gray"])'
  );
  const signupButton = document.querySelector("#signup-view button");
  const resetButton = document.querySelector("#forgot-view button");
  // ⚡️ NEW: Face ID Button ⚡️
  const faceIdButton = document.querySelector(
    '#login-view button[class*="flex items-center justify-center space-x-3 border border-gray-600"]:last-of-type'
  );

  const views = {
    login: document.getElementById("login-view"),
    signup: document.getElementById("signup-view"),
    forgot: document.getElementById("forgot-view"),
  };

  // --- Camera Gaze Logic (The Animation) ---
  let targetX = 0; // The desired pupil X position
  let targetY = 0; // The desired pupil Y position
  let currentX = 0; // The current pupil X position
  let currentY = 0; // The current pupil Y position
  const easing = 0.15; // Controls the "lag" or smoothing (0.01 to 1.0)
  const maxPupilMove = 16; // Max distance the pupil can move from center (in pixels)

  /**
   * Handles the mouse movement event and calculates the target position.
   */
  window.addEventListener("mousemove", (e) => {
    // 1. Get the camera lens's position relative to the viewport
    const lensRect = lens.getBoundingClientRect();

    // 2. Calculate the center coordinates of the camera lens
    const centerX = lensRect.left + lensRect.width / 2;
    const centerY = lensRect.top + lensRect.height / 2;

    // 3. Calculate the distance from the center of the camera to the mouse cursor
    const diffX = e.clientX - centerX;
    const diffY = e.clientY - centerY;

    // 4. Calculate the angle (in radians) from the camera center to the cursor
    const angle = Math.atan2(diffY, diffX);

    // 5. Convert the angle and constrained distance to a new X and Y position
    const pupilX = maxPupilMove * Math.cos(angle);
    const pupilY = maxPupilMove * Math.sin(angle);

    // 6. Update the target position
    targetX = pupilX;
    targetY = pupilY;
  });

  /**
   * The animation loop run by requestAnimationFrame.
   */
  function animate() {
    // Easing formula: current += (target - current) * easing
    currentX += (targetX - currentX) * easing;
    currentY += (targetY - currentY) * easing;

    // Apply the final movement, offsetting by 50% for centering
    pupil.style.transform = `translate(calc(-50% + ${currentX}px), calc(-50% + ${currentY}px))`;

    // Request the next frame for a continuous loop
    requestAnimationFrame(animate);
  }

  // Start the smooth animation loop
  animate();

  // --- View Switching Logic ---

  /**
   * Switches the visible form view and updates the header text.
   * @param {string} viewName - 'login', 'signup', or 'forgot'
   */
  function switchView(viewName) {
    // Hide all views first
    Object.values(views).forEach((v) => v.classList.add("hidden"));

    // Show the target view
    const targetView = views[viewName];
    if (targetView) {
      targetView.classList.remove("hidden");
    }

    // Update header text based on the view
    switch (viewName) {
      case "login":
        viewTitle.textContent = "Security Access";
        viewSubtitle.textContent = "Please authenticate to continue.";
        break;
      case "signup":
        viewTitle.textContent = "Create New Account";
        viewSubtitle.textContent =
          "The security camera is registering your face.";
        break;
      case "forgot":
        viewTitle.textContent = "Password Recovery";
        viewSubtitle.textContent = "Don't worry, the camera won't judge you.";
        break;
    }
  }

  // --- Event Listeners for Navigation ---

  // Login View links
  document.getElementById("signup-link").addEventListener("click", (e) => {
    e.preventDefault();
    switchView("signup");
  });
  document.getElementById("forgot-link").addEventListener("click", (e) => {
    e.preventDefault();
    switchView("forgot");
  });

  // Back to Login links
  document
    .getElementById("back-to-login-from-signup")
    .addEventListener("click", (e) => {
      e.preventDefault();
      switchView("login");
    });
  document
    .getElementById("back-to-login-from-forgot")
    .addEventListener("click", (e) => {
      e.preventDefault();
      switchView("login");
    });

  // Start on the login view
  switchView("login");

  // ==========================================================
  // --- CORRECTED FORM SUBMISSION LOGIC (Inside window.onload)
  // ==========================================================

  // LOGIN (Username/Password)
  if (loginButton) {
    loginButton.addEventListener("click", async (event) => {
      event.preventDefault();

      const email = loginUsernameInput.value; // Assuming 'Username' input takes email/username
      const password = loginPasswordInput.value;

      console.log("Login attempt:", email, password);

      try {
        const response = await fetch("/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        const result = await response.json();
        console.log(result);

        if (result.success) {
          alert("Login successful!");
          // Redirect to home.html after successful login
          window.location.href = "/home";
        } else {
          alert("Invalid credentials!");
        }
      } catch (error) {
        console.error("Login failed:", error);
        alert("Login failed due to a network error.");
      }
    });
  }

 // ⚡️ Face ID Login Logic ⚡️
if (faceIdButton) {
  faceIdButton.addEventListener("click", async (event) => {
    event.preventDefault();

    // Ensure video and canvas elements exist
    if (!video || !canvas || !context) {
      console.error("Camera elements (video/canvas) not found.");
      alert("Error: Camera elements missing from page.");
      return;
    }

    faceIdButton.disabled = true;
    viewSubtitle.textContent = "Requesting camera access...";
    faceIdButton.textContent = "Scanning...";

    let stream = null;

    try {
      // ⭐ STEP 1: Request camera access
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;

      // Wait for video to initialize
      await new Promise((resolve) => (video.onloadedmetadata = resolve));
      viewSubtitle.textContent = "Position your face in front of the camera...";

      // Small delay for user positioning
      await new Promise((resolve) => setTimeout(resolve, 1500));

      // ⭐ STEP 2: Capture frame
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Stop the camera stream
      stream.getTracks().forEach((track) => track.stop());

      // ⭐ STEP 3: Convert to Base64 image data
      const imageDataUrl = canvas.toDataURL("image/jpeg");

      // ⭐ STEP 4: Send image to backend for recognition
      viewSubtitle.textContent = "Verifying your identity...";
      const response = await fetch("/api/face-id-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: imageDataUrl }),
      });

      const result = await response.json();

      // ⭐ STEP 5: Handle response
      if (response.ok && result.success) {
        console.log("[SUCCESS] Face match confirmed:", result.identity);
        viewSubtitle.textContent = "✅ Face ID match confirmed!";
        alert("Face ID match confirmed! Access granted.");
        window.location.href = "/home";
      } else {
        console.warn("[WARN] Face ID failed:", result.message);
        viewSubtitle.textContent = "❌ Face ID failed. Try again.";
        alert(result.message || "Face ID failed. Please try again.");
      }
    } catch (error) {
      console.error("[ERROR] Face ID login failed:", error);
      alert("Face ID login failed. Please allow camera access and try again.");
      viewSubtitle.textContent = "Camera access failed.";
    } finally {
      // Clean up UI
      if (stream) stream.getTracks().forEach((track) => track.stop());
      faceIdButton.disabled = false;
      faceIdButton.textContent = "Use Face ID";
      setTimeout(() => {
        if (window.location.pathname !== "/home") {
          viewSubtitle.textContent = "Please authenticate to continue.";
        }
      }, 2500);
    }
  });
}

  // SIGNUP
  if (signupButton) {
    signupButton.addEventListener("click", async (event) => {
      event.preventDefault();

      const email = signupEmailInput.value;
      const password = signupPasswordInput.value;
      // ⚡️ UPDATED: Get the value from the new signupUsernameInput ⚡️
      const username = signupUsernameInput.value;

      try {
        const response = await fetch("/api/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          // Sending all three required fields
          body: JSON.stringify({ username, email, password }),
        });

        const result = await response.json();

        if (result.success) {
          alert("Signup successful! You can now log in.");
          // Optionally redirect or switch to login view
          switchView("login");
        } else {
          alert(result.message || "Signup failed. Please try again.");
        }
      } catch (error) {
        console.error("Signup failed:", error);
        alert("Signup failed due to a network error.");
      }
    });
  }

  // FORGOT PASSWORD
  if (resetButton) {
    resetButton.addEventListener("click", async (event) => {
      event.preventDefault();

      const email = forgotEmailInput.value;

      try {
        // Corrected endpoint
        const response = await fetch("/api/forgot-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });

        const result = await response.json();
        alert(result.message);
      } catch (error) {
        console.error("Password reset failed:", error);
        alert("Password reset failed due to a network error.");
      }
    });
  }
};