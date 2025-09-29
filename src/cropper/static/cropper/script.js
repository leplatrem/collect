document.addEventListener("DOMContentLoaded", () => {
  const CANVAS_SIZE_PIXELS = 400;
  const BACKGROUND_COLOR = "#fff";

  document.querySelectorAll(".square-cropper-widget").forEach(widget => {
    const canvas = widget.querySelector("canvas");
    canvas.width = CANVAS_SIZE_PIXELS;
    canvas.height = CANVAS_SIZE_PIXELS;
    const ctx = canvas.getContext("2d");

    const fileInput = widget.querySelector("input[type=file]");    
    const zoomInput = widget.querySelector("input[type=range]");
    const hiddenInput = widget.querySelector("input[type=hidden]");

    let img = new Image();
    let imgLoaded = false;
    let scale = 0;
    let pos = {x: 0, y: 0};
    // Drag state
    let origin = {x: 0, y: 0};
    let isDragging = false;

    function drawPreview(){
      if (!imgLoaded) {
        return;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = BACKGROUND_COLOR;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const w = img.width * scale;
      const h = img.height * scale;
      ctx.drawImage(img, pos.x, pos.y, w, h);
    }

    function exportCroppedImage() {
      if (!imgLoaded) return;

      // Determine the crop rectangle in original image coordinates
      const sx = (-pos.x / scale);
      const sy = (-pos.y / scale);
      const sWidth = CANVAS_SIZE_PIXELS / scale;
      const sHeight = CANVAS_SIZE_PIXELS / scale;

      // Create an offscreen canvas at original resolution
      const exportCanvas = document.createElement("canvas");
      exportCanvas.width = sWidth;
      exportCanvas.height = sHeight;
      const exportCtx = exportCanvas.getContext("2d");

      exportCtx.drawImage(img, sx, sy, sWidth, sHeight, 0, 0, sWidth, sHeight);

      // Export to hidden input as JPEG
      hiddenInput.value = exportCanvas.toDataURL("image/jpeg");
    }

    fileInput.addEventListener("change", e => {
      const file = e.target.files[0];
      if (!file) {
        return;
      }
      const url = URL.createObjectURL(file);
      img = new Image();
      img.onload = () => {
        imgLoaded = true;
        zoomInput.disabled = false;

        // Fit the image to canvas (smallest side)
        scale = Math.max(
          CANVAS_SIZE_PIXELS / img.width,
          CANVAS_SIZE_PIXELS / img.height
        );
        zoomInput.min = scale.toFixed(2);
        zoomInput.max = (scale * 3).toFixed(2);
        zoomInput.step = "0.01";
        zoomInput.value = scale.toFixed(2);
        // Center the image
        pos.x = (CANVAS_SIZE_PIXELS - img.width * scale) / 2;
        pos.y = (CANVAS_SIZE_PIXELS - img.height * scale) / 2;

        drawPreview();
        exportCroppedImage();
        URL.revokeObjectURL(url);
      }
      img.src = url;
    });

    zoomInput.addEventListener("input", e=>{
      if (!imgLoaded) {
        return;
      }
      const newScale = parseFloat(e.target.value);

      // Keep image centered on zoom
      const wOld = img.width * scale;
      const hOld = img.height * scale;
      const wNew = img.width * newScale;
      const hNew = img.height * newScale;

      pos.x -= (wNew - wOld) / 2;
      pos.y -= (hNew - hOld) / 2;
      pos.x = Math.max(Math.min(pos.x, 0), CANVAS_SIZE_PIXELS - img.width * newScale);
      pos.y = Math.max(Math.min(pos.y, 0), CANVAS_SIZE_PIXELS - img.height * newScale);

      scale = newScale;
      drawPreview();
      exportCroppedImage();
    });

    canvas.addEventListener("pointerdown", e=>{
      if(!imgLoaded) {
        return;
      }
      isDragging = true;
      origin.x = e.clientX;
      origin.y = e.clientY;
      canvas.setPointerCapture(e.pointerId);
    });

    canvas.addEventListener("pointermove", e=>{
      if (!isDragging) {
        return;
      }
      const dx = e.clientX - origin.x;
      const dy = e.clientY - origin.y;
      origin.x = e.clientX;
      origin.y = e.clientY;
      pos.x += dx;
      pos.y += dy;
      drawPreview();
      exportCroppedImage();
    });

    canvas.addEventListener("pointerup", () => {
      isDragging = false;

      pos.x = Math.max(Math.min(pos.x, 0), CANVAS_SIZE_PIXELS - img.width * scale);
      pos.y = Math.max(Math.min(pos.y, 0), CANVAS_SIZE_PIXELS - img.height * scale);
      drawPreview();
      exportCroppedImage();
    });

    canvas.addEventListener("pointercancel", () => {
      isDragging = false;
    });
  });
});
