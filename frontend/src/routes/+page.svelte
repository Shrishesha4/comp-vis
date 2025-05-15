<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  let videoElement: HTMLVideoElement;
  let canvasElement: HTMLCanvasElement;
  let stream: MediaStream | null = null;
  let captureInterval: number | null = null;
  let detectionResults: any[] = [];
  let isCapturing = false;
  let apiUrl = 'http://localhost:8844/process';
  let captureFrequency = 1000;
  let fileInput: HTMLInputElement;
  let selectedFile: File | null = null;
  let processingImage = false;
  let errorMessage = '';
  let activeTab = 'webcam';
  let showSettings = false;
  let helmetCount = 0;
  let noHelmetCount = 0;
  let totalDetections = 0;
  let helmetPercentage = 0;

  async function startWebcam() {
    try {
      errorMessage = '';
      stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 1280 },
          height: { ideal: 720 }
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

  function stopWebcam() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }
    
    if (videoElement && videoElement.srcObject) {
      videoElement.srcObject = null;
    }
    
    if (isCapturing) {
      stopCapturing();
    }
  }

  function startCapturing() {
    if (!stream) {
      startWebcam();
      setTimeout(() => {
        isCapturing = true;
        captureInterval = window.setInterval(captureFrame, captureFrequency);
      }, 1000);
    } else {
      isCapturing = true;
      captureInterval = window.setInterval(captureFrame, captureFrequency);
    }
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
      // Clear previous results
      detectionResults = [];
      updateStatistics();
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
      
      // Update statistics
      updateStatistics();
      
      // If we're processing a static image, draw the results
      if ((selectedFile || !isCapturing) && canvasElement) {
        if (selectedFile) {
          drawImageWithDetections(selectedFile, detectionResults);
        }
      } else if (isCapturing && canvasElement) {
        // Draw detection boxes on the live feed
        drawDetectionsOnLiveFrame(detectionResults);
      }
    } catch (err) {
      console.error('Error sending image to API:', err);
      errorMessage = 'Failed to communicate with the detection server.';
    }
  }

  // Update statistics based on detection results
  function updateStatistics() {
    totalDetections = detectionResults.length;
    helmetCount = detectionResults.filter(d => d.has_helmet).length;
    noHelmetCount = totalDetections - helmetCount;
    helmetPercentage = totalDetections > 0 ? Math.round((helmetCount / totalDetections) * 100) : 0;
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
        drawDetectionBoxes(context, detections);
      };
      img.src = e.target?.result as string;
    };
    reader.readAsDataURL(imageFile);
  }

  // Draw detection boxes on the current frame
  function drawDetectionsOnLiveFrame(detections: any[]) {
    if (!canvasElement) return;
    
    const context = canvasElement.getContext('2d');
    if (!context) return;
    
    // The frame is already drawn by captureFrame()
    // Just add the detection boxes
    drawDetectionBoxes(context, detections);
  }

  // Draw detection boxes on a canvas context
  function drawDetectionBoxes(context: CanvasRenderingContext2D, detections: any[]) {
    // Draw detection boxes
    detections.forEach(detection => {
      const [x, y, width, height] = detection.bbox;
      const hasHelmet = detection.has_helmet;
      
      // Set box style based on helmet detection
      context.strokeStyle = hasHelmet ? '#10b981' : '#ef4444';
      context.lineWidth = 3;
      context.strokeRect(x, y, width, height);
      
      // Add label background
      const text = `${hasHelmet ? 'Helmet' : 'No Helmet'} (${Math.round(detection.confidence * 100)}%)`;
      const textWidth = context.measureText(text).width + 10;
      context.fillStyle = hasHelmet ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)';
      context.fillRect(x, y - 25, textWidth, 20);
      
      // Add label text
      context.fillStyle = 'white';
      context.font = 'bold 14px Arial';
      context.fillText(text, x + 5, y - 10);
    });
  }

  // Switch between tabs
  function switchTab(tab: string) {
    activeTab = tab;
    
    // If switching away from webcam, stop it
    if (tab !== 'webcam' && stream) {
      stopWebcam();
    }
    
    // If switching to webcam, start it
    if (tab === 'webcam' && !stream) {
      startWebcam();
    }
  }

  // Toggle settings panel
  function toggleSettings() {
    showSettings = !showSettings;
  }

  // Clean up on component unmount
  onDestroy(() => {
    stopCapturing();
    stopWebcam();
  });

  // Initialize webcam on mount if on webcam tab
  onMount(() => {
    if (activeTab === 'webcam') {
      startWebcam();
    }
  });
</script>

<main class="min-h-screen bg-gray-100">
  <div class="max-w-7xl mx-auto px-4 py-6">
    <!-- Header -->
    <header class="bg-white shadow-md rounded-lg p-6 mb-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-800">Real-time Motorcycle Helmet Detection</h1>
          <p class="text-gray-600 mt-1">Real-time detection of motorcycle riders and their helmet usage</p>
        </div>
        
        <div class="mt-4 md:mt-0 flex items-center">
          <button 
            on:click={toggleSettings}
            class="flex items-center px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
            </svg>
            Settings
          </button>
        </div>
      </div>
      
      <!-- Settings Panel (Collapsible) -->
      {#if showSettings}
        <div class="mt-6 p-4 bg-gray-50 rounded-md border border-gray-200 transition-all">
          <h3 class="text-lg font-medium text-gray-800 mb-3">Detection Settings</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Capture Frequency (ms):
              </label>
              <input 
                type="range" 
                bind:value={captureFrequency} 
                min="500" 
                max="5000" 
                step="100"
                class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <div class="flex justify-between text-xs text-gray-500 mt-1">
                <span>Fast (500ms)</span>
                <span>{captureFrequency}ms</span>
                <span>Slow (5000ms)</span>
              </div>
            </div>
            
            <div>
              <p class="text-sm text-gray-600 mb-2">
                Adjust the frequency at which frames are captured and processed. 
                Faster rates provide more real-time feedback but may use more resources.
              </p>
            </div>
          </div>
        </div>
      {/if}
      
      <!-- Tab Navigation -->
      <div class="flex mt-6 border-b border-gray-200">
        <button 
          class={`px-4 py-2 font-medium text-sm ${activeTab === 'webcam' ? 'text-blue-600 border-b-2 border-blue-500' : 'text-gray-500 hover:text-gray-700'}`}
          on:click={() => switchTab('webcam')}
        >
          Webcam Detection
        </button>
        <button 
          class={`px-4 py-2 font-medium text-sm ${activeTab === 'upload' ? 'text-blue-600 border-b-2 border-blue-500' : 'text-gray-500 hover:text-gray-700'}`}
          on:click={() => switchTab('upload')}
        >
          Image Upload
        </button>
      </div>
    </header>
    
    <!-- Main Content -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Panel: Input Source -->
      <div class="lg:col-span-2">
        <div class="bg-white shadow-md rounded-lg overflow-hidden">
          <!-- Webcam Tab -->
          {#if activeTab === 'webcam'}
            <div class="p-4">
              <h2 class="text-xl font-semibold text-gray-800 mb-4">Live Camera Feed</h2>
              
              <div class="relative">
                <!-- svelte-ignore a11y_media_has_caption -->
                <video 
                  bind:this={videoElement} 
                  class="w-full h-auto border rounded-lg bg-black"
                  autoplay 
                  playsinline
                ></video>
                
                {#if !stream}
                  <div class="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 rounded-lg">
                    <button 
                      on:click={startWebcam}
                      class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
                      </svg>
                      Start Camera
                    </button>
                  </div>
                {/if}
              </div>
              
              <div class="flex flex-wrap gap-2 mt-4">
                {#if stream && !isCapturing}
                  <button 
                    on:click={startCapturing} 
                    class="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center justify-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
                    </svg>
                    Start Detection
                  </button>
                {/if}
                
                {#if isCapturing}
                  <button 
                    on:click={stopCapturing} 
                    class="flex-1 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors flex items-center justify-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                    Pause Detection
                  </button>
                {/if}
                
                {#if stream}
                  <button 
                    on:click={stopWebcam} 
                    class="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center justify-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                    Stop Camera
                  </button>
                {/if}
              </div>
            </div>
          {/if}
          
          <!-- Upload Tab -->
          {#if activeTab === 'upload'}
            <div class="p-4">
              <h2 class="text-xl font-semibold text-gray-800 mb-4">Image Upload</h2>
              
              <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                
                <p class="mt-1 text-sm text-gray-600">
                  Upload an image to detect helmet usage
                </p>
                
                <div class="mt-4">
                  <input 
                    type="file" 
                    bind:this={fileInput}
                    on:change={handleFileSelect}
                    accept="image/*"
                    class="hidden"
                    id="file-upload"
                  />
                  <label 
                    for="file-upload"
                    class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors cursor-pointer inline-block"
                  >
                    Select Image
                  </label>
                  
                  {#if selectedFile}
                    <p class="mt-2 text-sm text-gray-600">
                      Selected: {selectedFile.name}
                    </p>
                  {/if}
                </div>
              </div>
              
              <button 
                on:click={processFile} 
                class="mt-4 w-full px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!selectedFile || processingImage}
              >
                {processingImage ? 'Processing...' : 'Analyze Image'}
              </button>
            </div>
          {/if}
          
          <!-- Detection Canvas -->
          <div class="p-4 border-t border-gray-200">
            <h3 class="text-lg font-medium text-gray-800 mb-3">Detection Results</h3>
            
            <canvas 
              bind:this={canvasElement} 
              class="w-full border rounded-lg bg-white"
            ></canvas>
            
            {#if errorMessage}
              <div class="mt-4 p-3 bg-red-100 text-red-700 rounded-lg flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
                {errorMessage}
              </div>
            {/if}
          </div>
        </div>
      </div>
      
      <!-- Right Panel: Statistics and Results -->
      <div class="lg:col-span-1">
        <div class="bg-white shadow-md rounded-lg p-4">
          <h2 class="text-xl font-semibold text-gray-800 mb-4">Detection Statistics</h2>
          
          <!-- Statistics Cards -->
          <div class="grid grid-cols-2 gap-4 mb-6">
            <div class="bg-blue-50 p-4 rounded-lg border border-blue-100">
              <p class="text-sm text-blue-600 font-medium">Total Detected</p>
              <p class="text-2xl font-bold text-blue-800">{totalDetections}</p>
            </div>
            
            <div class="bg-green-50 p-4 rounded-lg border border-green-100">
              <p class="text-sm text-green-600 font-medium">With Helmet</p>
              <p class="text-2xl font-bold text-green-800">{helmetCount}</p>
            </div>
            
            <div class="bg-red-50 p-4 rounded-lg border border-red-100">
              <p class="text-sm text-red-600 font-medium">Without Helmet</p>
              <p class="text-2xl font-bold text-red-800">{noHelmetCount}</p>
            </div>
            
            <div class="bg-purple-50 p-4 rounded-lg border border-purple-100">
              <p class="text-sm text-purple-600 font-medium">Helmet Usage</p>
              <p class="text-2xl font-bold text-purple-800">{helmetPercentage}%</p>
            </div>
          </div>
          
          <!-- Detailed Results -->
          {#if detectionResults.length > 0}
            <div>
              <h3 class="text-lg font-medium text-gray-800 mb-3">Detailed Results</h3>
              
              <div class="max-h-96 overflow-y-auto pr-2">
                <ul class="space-y-2">
                  {#each detectionResults as detection, i}
                    <li class="p-3 rounded-lg border {detection.has_helmet ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}">
                      <div class="flex justify-between items-center">
                        <span class="font-medium {detection.has_helmet ? 'text-green-700' : 'text-red-700'}">
                          Person {i+1}
                        </span>
                        <span class="text-sm {detection.has_helmet ? 'text-green-600' : 'text-red-600'}">
                          Confidence: {Math.round(detection.confidence * 100)}%
                        </span>
                      </div>
                      <p class="text-sm mt-1 {detection.has_helmet ? 'text-green-600' : 'text-red-600'}">
                        {detection.has_helmet ? '✓ Wearing helmet' : '✗ No helmet detected'}
                      </p>
                    </li>
                  {/each}
                </ul>
              </div>
            </div>
          {:else}
            <div class="text-center py-8 text-gray-500">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p class="mt-2">No detections yet</p>
              <p class="text-sm mt-1">Start detection or upload an image to see results</p>
            </div>
          {/if}
        </div>
      </div>
    </div>
    
    <!-- Footer -->
    <footer class="mt-8 text-center text-gray-500 text-sm">
      <p>Real-Time Helmet Detection System for Motorcycle Riders - Capstone Project - By Shrishesha Narmatesshvara V - 192321183 - Dr. J. Velmurgan</p>
    </footer>
  </div>
</main>
