import os
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from single_post_pipeline import run_single_post_pipeline
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Toronto Minutes API")

class PipelineResponse(BaseModel):
    status: str
    message: str

@app.get("/")
async def root():
    return {"message": "Toronto Minutes API is live. Use POST /run to trigger the pipeline."}

@app.post("/run", response_model=PipelineResponse)
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """
    Triggers the Instagram automation pipeline in the background.
    """
    logger.info("Pipeline trigger received.")
    
    # Run the pipeline in the background so the API call returns immediately
    background_tasks.add_task(run_single_post_pipeline)
    
    return {
        "status": "accepted",
        "message": "Pipeline started in the background. Check logs for progress."
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
