# Beginner Setup Guide

Follow these steps to set up and run the **FaceChain Verifier** pipeline.

---

## Part A: Get the Free SerpApi Key

1. Open <https://serpapi.com/users/sign_up> and register for a free account.
2. After signing in, go to <https://serpapi.com/manage-api-key>.
3. Copy **Your Private API Key**.
4. In the project folder, open `.env` (or copy `.env.example` to `.env`).
5. Paste your API key:
   ```text
   SERPAPI_KEY=your_actual_key_here
   ```
6. Save `.env`. (Never share or commit this file).

---

## Part B: Prepare the Test Image

1. Place your front-facing test photo in the project directory as `sample.jpg`.
2. The pipeline supports two ways to search:
   - **Direct URL (Recommended)**: Provide `--image-url "https://..."` with a direct link (e.g. from GitHub Raw, Imgur, or Unsplash).
   - **Automatic Host**: If you do not pass `--image-url`, the tool will automatically host `sample.jpg` to a temporary direct host.

---

## Part C: Run the Pipeline

Open a terminal in the project directory and run:

```powershell
# 1. Activate environment and install dependencies
python -m pip install -r requirements.txt

# 2. Run the end-to-end pipeline
python main.py run --image sample.jpg --image-url "YOUR_IMAGE_URL" --preferred-domain instagram.com
```

---

## Part D: Test Blockchain Anti-Tamper Detection

Demonstrate fraud detection for your screen recording:

```powershell
python main.py tamper --chain output/blockchain.json
```

---

## Part E: Run Automated Test Suite

```powershell
python -m pytest -v
```

All 6 automated tests should show `PASSED`.
