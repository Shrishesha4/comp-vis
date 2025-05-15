# Motorcycle Helmet Detection System

This project implements a computer vision system to detect motorcycle riders and check if they are wearing helmets.

## Project Structure

- `frontend/`: Svelte-based web interface
- `backend/`: Python Flask API with OpenCV and PyTorch

## Frontend

The frontend is built with Svelte and provides:
- Webcam video stream capture
- Video file input
- Frame capture and processing
- Display of detection results with bounding boxes

### Setup and Run

```bash
cd frontend
npm install
npm run dev