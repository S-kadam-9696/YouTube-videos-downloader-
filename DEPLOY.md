# Deployment

This project is prepared for a Docker-based web deployment.

## Render
1. Push this folder to a GitHub repository.
2. In Render, create a new Web Service from the repository.
3. Render can use the included `render.yaml`, or select Docker as the runtime.
4. The Dockerfile installs FFmpeg and starts FastAPI with Uvicorn.
5. Keep the service on the free plan if it is available for your account/region.

The application listens on the `PORT` environment variable.

## Important
AdSense code is already included in `app/static/index.html`.
AdSense approval and ad serving are controlled by Google and are not guaranteed by deployment.
