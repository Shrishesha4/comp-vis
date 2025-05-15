<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  // State variables
  let videoElement: HTMLVideoElement;
  let canvasElement: HTMLCanvasElement;
  let stream: MediaStream | null = null;
  let captureInterval: number | null = null;
  let detectionResults: any[] = [];
  let isCapturing = false;
  let apiUrl = 'http://localhost:8844/process';
  let captureFrequency = 1000; // 1 second
  let fileInput: HTMLInputElement;
  let selectedFile: File | null = null;
  let processingImage = false;
  let errorMessage = '';

  // Start webcam stream
  async function startWebcam() {
    try {
      errorMessage = '';
      stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 },
          height: { ideal: 480 }
        } 
      });
      
      if (videoElement) {
        videoElement.srcObject = stream;
        videoElement.play();
      }
    } catch (err) {
      console.error('Error accessing webcam:', err);
      errorMessage = 'Could not access webcam. Please ensure you have granted permission.';
    }
  }

  // Stop webcam stream
  function stopWebcam() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }
    
    if (videoElement && videoElement.srcObject) {
      videoElement.srcObject = null;
    }
  }

  // Start capturing frames
  function startCapturing() {
    if (!stream) {
      startWebcam();
    }
    
    isCapturing = true;
    captureInterval = window.setInterval(captureFrame, captureFrequency);
  }

  // Stop capturing frames
  function stopCapturing() {
    isCapturing = false;
    if (captureInterval) {
      clearInterval(captureInterval);
      captureInterval = null;
    }
  }

  // Capture a single frame from video
  function captureFrame() {
    if (!videoElement || !canvasElement) return;
    
    const context = canvasElement.getContext('2d');
    if (!context) return;
    
    // Set canvas dimensions to match video
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    
    // Draw video frame to canvas
    context.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
    
    // Convert canvas to blob and send to API
    canvasElement.toBlob(async (blob) => {
      if (blob) {
        await sendImageToAPI(blob);
      }
    }, 'image/jpeg', 0.9);
  }

  // Handle file selection
  function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      selectedFile = input.files[0];
    }
  }

  // Process selected file
  async function processFile() {
    if (!selectedFile) {
      errorMessage = 'Please select a file first';
      return;
    }
    
    processingImage = true;
    errorMessage = '';
    
    try {
      await sendImageToAPI(selectedFile);
    } catch (err) {
      console.error('Error processing file:', err);
      errorMessage = 'Failed to process the image. Please try again.';
    } finally {
      processingImage = false;
    }
  }

  // Send image to backend API
  async function sendImageToAPI(imageData: Blob | File) {
    try {
      const formData = new FormData();
      formData.append('image', imageData);
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
      
      const result = await response.json();
      detectionResults = result.detections || [];
      
      // If we're processing a static image, draw the results
      if (selectedFile && canvasElement) {
        drawImageWithDetections(selectedFile, detectionResults);
      }
    } catch (err) {
      console.error('Error sending image to API:', err);
      errorMessage = 'Failed to communicate with the detection server.';
    }
  }

  // Draw image with detection boxes
  function drawImageWithDetections(imageFile: File, detections: any[]) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        if (!canvasElement) return;
        
        const context = canvasElement.getContext('2d');
        if (!context) return;
        
        // Set canvas size to match image
        canvasElement.width = img.width;
        canvasElement.height = img.height;
        
        // Draw the image
        context.drawImage(img, 0, 0);
        
        // Draw detection boxes
        detections.forEach(detection => {
          const [x, y, width, height] = detection.bbox;
          const hasHelmet = detection.has_helmet;
          
          // Set box style based on helmet detection
          context.strokeStyle = hasHelmet ? 'green' : 'red';
          context.lineWidth = 3;
          context.strokeRect(x, y, width, height);
          
          // Add label
          context.fillStyle = hasHelmet ? 'green' : 'red';
          context.font = '16px Arial';
          context.fillText(
            `${hasHelmet ? 'Helmet' : 'No Helmet'} (${Math.round(detection.confidence * 100)}%)`,
            x, y - 5
          );
        });
      };
      img.src = e.target?.result as string;
    };
    reader.readAsDataURL(imageFile);
  }

  // Clean up on component unmount
  onDestroy(() => {
    stopCapturing();
    stopWebcam();
  });
</script>

<main class="container mx-auto p-4">
  <h1 class="text-3xl font-bold mb-6">Motorcycle Helmet Detection</h1>
  
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="border rounded-lg p-4 bg-gray-50">
      <h2 class="text-xl font-semibold mb-4">Video Input</h2>
      
      <div class="mb-4">
        <video 
          bind:this={videoElement} 
          class="w-full border rounded-lg bg-black"
          autoplay 
          playsinline
        ></video>
      </div>
      
      <div class="flex flex-wrap gap-2 mb-4">
        <button 
          on:click={startWebcam} 
          class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          disabled={!!stream}
        >
          Start Camera
        </button>
        
        <button 
          on:click={stopWebcam} 
          class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          disabled={!stream}
        >
          Stop Camera
        </button>
        
        <button 
          on:click={startCapturing} 
          class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
          disabled={isCapturing || !stream}
        >
          Start Detection
        </button>
        
        <button 
          on:click={stopCapturing} 
          class="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
          disabled={!isCapturing}
        >
          Stop Detection
        </button>
      </div>
      
      <div class="mb-4">
        <label class="block mb-2">Capture Frequency (ms):</label>
        <input 
          type="number" 
          bind:value={captureFrequency} 
          min="500" 
          max="5000" 
          step="100"
          class="w-full p-2 border rounded"
        />
      </div>
    </div>
    
    <div class="border rounded-lg p-4 bg-gray-50">
      <h2 class="text-xl font-semibold mb-4">Image Upload</h2>
      
      <div class="mb-4">
        <input 
          type="file" 
          bind:this={fileInput}
          on:change={handleFileSelect}
          accept="image/*"
          class="w-full p-2 border rounded"
        />
      </div>
      
      <button 
        on:click={processFile} 
        class="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 mb-4"
        disabled={!selectedFile || processingImage}
      >
        {processingImage ? 'Processing...' : 'Process Image'}
      </button>
    </div>
  </div>
  
  <div class="mt-6 border rounded-lg p-4 bg-gray-50">
    <h2 class="text-xl font-semibold mb-4">Detection Results</h2>
    
    <canvas 
      bind:this={canvasElement} 
      class="w-full border rounded-lg bg-white"
    ></canvas>
    
    {#if errorMessage}
      <div class="mt-4 p-3 bg-red-100 text-red-700 rounded">
        {errorMessage}
      </div>
    {/if}
    
    {#if detectionResults.length > 0}
      <div class="mt-4">
        <h3 class="text-lg font-medium mb-2">Detected Objects:</h3>
        <ul class="list-disc pl-5">
          {#each detectionResults as detection, i}
            <li class={detection.has_helmet ? 'text-green-600' : 'text-red-600'}>
              Person {i+1}: {detection.has_helmet ? 'Wearing helmet' : 'No helmet'} 
              (Confidence: {Math.round(detection.confidence * 100)}%)
            </li>
          {/each}
        </ul>
      </div>
    {/if}
  </div>
</main>
