(function () {
  const root = document.documentElement;
  const themeToggle = document.getElementById("themeToggle");

  function applyTheme(theme) {
    root.setAttribute("data-bs-theme", theme);
    localStorage.setItem("theme", theme);
  }

  const savedTheme = localStorage.getItem("theme") || "dark";
  applyTheme(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const current = root.getAttribute("data-bs-theme") || "dark";
      applyTheme(current === "dark" ? "light" : "dark");
    });
  }

  // Auto-dismiss Flash Alerts
  setTimeout(() => {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alertElement => {
      if (typeof bootstrap !== 'undefined') {
        const bsAlert = new bootstrap.Alert(alertElement);
        bsAlert.close();
      } else {
        alertElement.remove();
      }
    });
  }, 500);

  const uploadForm = document.getElementById("uploadForm");
  if (!uploadForm) {
    return;
  }

  const submitBtn = document.getElementById("submitBtn");
  const submitSpinner = document.getElementById("submitSpinner");
  const translatorEngine = document.getElementById("translator_engine");
  const openaiModel = document.getElementById("openai_model");
  const openaiApiKey = document.getElementById("openai_api_key");
  const volumeInput = document.getElementById("original_volume");
  const volumeValue = document.getElementById("volumeValue");
  const progressCard = document.getElementById("progressCard");
  const progressText = document.getElementById("progressText");
  const progressBar = document.getElementById("progressBar");
  const resultCard = document.getElementById("resultCard");
  const resultVideo = document.getElementById("resultVideo");
  const downloadVideo = document.getElementById("downloadVideo");
  const downloadSrt = document.getElementById("downloadSrt");
  const elapsedInfo = document.getElementById("elapsedInfo");

  function setSubmitting(isSubmitting) {
    submitBtn.disabled = isSubmitting;
    submitSpinner.classList.toggle("d-none", !isSubmitting);
  }

  // Hiển thị thông báo dạng toast (không chặn UI như alert)
  function showToast(message, type) {
    type = type || "danger";
    let container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container position-fixed top-0 end-0 p-3";
      container.style.zIndex = "1080";
      document.body.appendChild(container);
    }
    const iconMap = {
      danger: "bi-exclamation-triangle-fill",
      warning: "bi-exclamation-circle-fill",
      success: "bi-check-circle-fill",
      info: "bi-info-circle-fill",
    };
    const wrapper = document.createElement("div");
    wrapper.className = `toast align-items-center text-bg-${type} border-0 toast-alert`;
    wrapper.setAttribute("role", "alert");
    wrapper.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          <i class="bi ${iconMap[type] || iconMap.danger} me-2"></i>${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>`;
    container.appendChild(wrapper);
    if (typeof bootstrap !== "undefined") {
      const toast = new bootstrap.Toast(wrapper, { delay: 6000 });
      toast.show();
      wrapper.addEventListener("hidden.bs.toast", () => wrapper.remove());
    } else {
      wrapper.style.display = "block";
      setTimeout(() => wrapper.remove(), 6000);
    }
  }

  function updateProgress(progress, message) {
    const value = Number(progress) || 0;
    progressCard.classList.remove("d-none");
    progressBar.style.width = `${value}%`;
    progressBar.textContent = `${value}%`;
    progressText.textContent = message || "Dang xu ly...";
  }

  function showResult(result) {
    if (!result || !result.video_url) return;
    resultCard.classList.remove("d-none");
    resultVideo.src = result.video_url;
    resultVideo.load();
    downloadVideo.href = result.video_url;
    downloadVideo.download = result.video_name || "output.mp4";

    if (result.srt_url) {
      downloadSrt.classList.remove("d-none");
      downloadSrt.href = result.srt_url;
      downloadSrt.download = result.srt_name || "subtitle.srt";
    } else {
      downloadSrt.classList.add("d-none");
    }
    elapsedInfo.textContent = `Thoi gian xu ly: ${result.elapsed_seconds || 0}s`;
  }

  function pollProgress(jobId) {
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`/api/progress/${jobId}`);
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || "Khong lay duoc tien trinh.");
        }
        updateProgress(data.progress, data.message);

        if (data.status === "done") {
          clearInterval(timer);
          setSubmitting(false);
          showResult(data.result);
        }
        if (data.status === "failed") {
          clearInterval(timer);
          setSubmitting(false);
          showToast(data.message || "Xử lý thất bại.", "danger");
        }
      } catch (err) {
        clearInterval(timer);
        setSubmitting(false);
        showToast(err.message || "Có lỗi khi theo dõi tiến trình.", "danger");
      }
    }, 1200);
  }

  function syncTranslatorFields() {
    const usingOpenAI = translatorEngine.value === "openai";
    openaiModel.disabled = !usingOpenAI;
    openaiApiKey.disabled = !usingOpenAI;
    openaiModel.classList.toggle("opacity-50", !usingOpenAI);
    openaiApiKey.classList.toggle("opacity-50", !usingOpenAI);
  }

  volumeInput.addEventListener("input", (e) => {
    volumeValue.textContent = e.target.value;
  });

  translatorEngine.addEventListener("change", syncTranslatorFields);
  syncTranslatorFields();

  const videoInput = document.getElementById("video");
  const videoPreviewContainer = document.getElementById("videoPreviewContainer");
  const videoPreview = document.getElementById("videoPreview");
  const clearVideoBtn = document.getElementById("clearVideoBtn");
  const dropzoneLabel = document.getElementById("dropzoneLabel");

  function closeVideoPreview() {
    if (videoInput) videoInput.value = "";
    if (videoPreviewContainer) videoPreviewContainer.classList.add("d-none");
    if (videoPreview) videoPreview.src = "";
    if (dropzoneLabel) dropzoneLabel.classList.remove("d-none");
  }

  if (videoInput && videoPreviewContainer) {
    videoInput.addEventListener("change", function () {
      const file = this.files[0];
      if (file) {
        const fileUrl = URL.createObjectURL(file);
        videoPreview.src = fileUrl;
        videoPreviewContainer.classList.remove("d-none");
        if (dropzoneLabel) dropzoneLabel.classList.add("d-none");
      } else {
        closeVideoPreview();
      }
    });

    if (clearVideoBtn) {
      clearVideoBtn.addEventListener("click", function () {
        closeVideoPreview();
      });
    }
  }

  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setSubmitting(true);
    resultCard.classList.add("d-none");
    updateProgress(1, "Dang gui video...");



    try {
      const formData = new FormData(uploadForm);
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Upload that bai.");
      }
      pollProgress(data.job_id);
    } catch (err) {
      setSubmitting(false);
      showToast(err.message || "Không thể tải video lên.", "danger");
    }
  });

})();
