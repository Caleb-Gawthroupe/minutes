# Toronto Minutes — Civic Automation Pipeline

Toronto Minutes is an agentic tool designed to bridge the gap between complex municipal government documents and public awareness. It automatically scrapes Toronto City Council meetings, bylaws, and reports, then uses RAG-enhanced AI to generate high-impact social media carousels.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Node.js** (required for Playwright's browser engine)
- **API Keys**:
  - `OPENROUTER_API_KEY`: For AI generation (Ollama/OpenAI compatible).
  - `INSTAGRAM_ACCESS_TOKEN` & `INSTAGRAM_USER_ID`: For automated posting.
  - `IMGBB_API_KEY` (Optional): Alternative image hosting.
  - `PEXELS_API_KEY` (Optional): For high-quality background sourcing.

### 2. Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Caleb-Gawthroupe/minutes.git
   cd minutes
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**:
   The pipeline uses headless Chromium for scraping PDFs and rendering graphics.
   ```bash
   playwright install chromium
   ```

4. **Setup Environment**:
   Create a `.env` file in the root directory:
   ```env
   OPENROUTER_API_KEY=your_key_here
   OPENROUTER_MODEL=openrouter/hunter-alpha
   INSTAGRAM_ACCESS_TOKEN=your_ig_token
   INSTAGRAM_USER_ID=your_ig_id
   IMGBB_API_KEY=your_imgbb_key
   PEXELS_API_KEY=your_pexels_key
   ```

---

## 🏃 Running the Pipeline

To run the full end-to-end pipeline once:

```bash
python3 single_post_pipeline.py
```

### What happens?
1. **Scraping**: Fetches the latest agenda items from Toronto TMMIS and recent bylaws.
2. **Ingestion**: Documents are chunked and stored in a local **ChromaDB** vector store (`data/chroma_db`).
3. **Selection**: AI identifies the most "human-centric" trending topic (e.g., Housing, Transit).
4. **RAG Deep-Dive**: AI performs a RAG search against the vector store to find historical context and contradictions.
5. **Creative Generation**: AI generates a caption and content for 3 specific slides:
   - *Slide 1*: The Decision (Plain language hook).
   - *Slide 2*: The Numbers (Hard stats).
   - *Slide 3*: What it Means (Resident impact).
6. **Rendering**: Uses Playwright to render premium CSS3/HTML5 social cards to `downloads/visuals/`.
7. **Cloud Upload**: Uploads images to Catbox/ImgBB for public accessibility.
8. **Instagram Post**: Publishes a multi-slide carousel via the Instagram Graph API.

---

## ☁️ Cloud Hosting & Scheduling (Free Tier)

### 1. 24/7 Automated Scheduling (GitHub Actions)
The project includes a GitHub Actions workflow to run the pipeline automatically every day.

- **Setup**:
  1. Push your code to a **GitHub Repository**.
  2. Go to `Settings` -> `Secrets and variables` -> `Actions`.
  3. Add the following **Repository Secrets**:
     - `OPENROUTER_API_KEY`
     - `INSTAGRAM_ACCESS_TOKEN`
     - `INSTAGRAM_USER_ID`
     - `PEXELS_API_KEY` (optional)
     - `IMGBB_API_KEY` (optional)
  4. The workflow will run automatically at **9:00 AM EST** daily. You can also trigger it manually from the `Actions` tab.

### 2. Live API Trigger (Render / Koyeb)
You can trigger the pipeline on-demand using a simple API call. The project includes a **FastAPI** server for this purpose.

- **Local Development**:
  ```bash
  python3 src/api_server.py
  ```
- **Deployment**:
  1. Deploy the Dockerized application to **Render** or **Koyeb**.
  2. The server will run on port `8080` (or the port specified by the `$PORT` environment variable).
  3. **Trigger via API**: Send a POST request to your public URL:
     ```bash
     curl -X POST https://your-app-url.render.com/run
     ```
- **Note**: Render's free tier sleeps after 15 minutes of inactivity. Use a service like **Cron-job.org** to ping your `/` endpoint every 10 minutes to keep it awake if needed.

---

## 🛠️ Troubleshooting

- **ChromaDB KEYERROR**: If you see `KeyError: '_type'`, it's a version mismatch. Delete the database folder and re-run: `rm -rf data/chroma_db`.
- **Instagram 400 Error**: Ensure your `INSTAGRAM_USER_ID` is the **Business ID**, not your personal account ID, and that your token has `instagram_basic` and `instagram_content_publish` permissions.
- **Playwright Errors**: If running in a CI/HEADLESS environment, ensure `xvfb-run` is used as per the Dockerfile.
