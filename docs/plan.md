# Project Plan: Astor Kino Notifier (KinoWeek)

### 1\. Project Summary

This project will create an automated system to scrape the "Original Version" (OV) movie schedule from the Astor Grand Cinema Hannover website. The script will run automatically every Monday, collect the full week's showtimes, format them into a clean report, and send it directly to you via a Telegram message.

  * **Technology Stack:** Python (with `uv`), Playwright, Docker
  * **Host:** Hetzner VPS (managed via Coolify)
  * **Notification:** Telegram Bot

### 2\. Core Requirements Checklist

  * [x] **Extract All Movies:** Scrape all movie titles listed for the week.
  * [x] **Extract All Days:** Dynamically read all available date tabs (e.g., "Mon 17.11," "Tue 18.11," etc.).
  * [x] **Extract Full Schedule:** Get all showtimes, including cinema hall and version (OV/OmU), for each movie under each day.
  * [x] **Run Automatically:** Schedule the script to run once per week (e.g., every Monday evening).
  * [x] **Hosted Solution:** Deploy on your Hetzner VPS using Coolify so your laptop is not required.
  * [x] **Notification:** Send a formatted message via Telegram.

### 3\. Technical Architecture & Workflow

The system is built on four components:

1.  **The Scraper (`scrape_movies.py`):** A Python script using **Playwright**. It launches a headless browser, navigates the dynamic website, clicks each date tab, and extracts the schedule.
2.  **The Container (`Dockerfile`):** A Dockerfile that packages your Python script, the `uv` environment, and all dependencies (including the Playwright browser binaries) into a portable image.
3.  **The Host & Scheduler (`Coolify`):** Your existing Coolify instance on Hetzner will be used. We will set up a **Scheduled Task** service that pulls the image and runs it based on a cron schedule.
4.  **The Notifier (`Telegram`):** The Python script will use the `requests` library to send the final formatted schedule to the Telegram Bot API, which pushes it to your phone.

### 4\. Scraper Logic: Step-by-Step

The `scrape_movies.py` script will perform the following actions:

1.  **Launch:** Start a headless Playwright browser.
2.  **Navigate:** Open the URL `https://hannover.premiumkino.de/programm/originalfassung`.
3.  **Handle Cookies:** (If present) Find and click the "accept" button for the cookie banner.
4.  **Find Date Tabs:** The script will locate the list of date tabs (e.g., using a CSS selector like `.date-selector .nav-link`).
5.  **Initialize Storage:** Create an empty dictionary, `schedule_data = {}`, to hold the results.
6.  **Loop Through Dates:** The script will iterate through each date tab found:
      * Get the day and date text (e.g., "Mon 24.11").
      * Click the tab element.
      * **Wait for JS:** This is the key step. The script will explicitly wait for the movie list section to update (e.g., `page.wait_for_selector("div.movie-list-item")`).
      * **Scrape Movies:** Once the new day's content is loaded, it will find all movie blocks.
      * **Inner Loop (Showtimes):** For each movie, it will:
          * Extract the **Title** (e.g., "Wicked: Part 2").
          * Find all showtime elements associated with it.
          * For each showtime, extract the **Time** (e.g., "19:30"), **Version** (e.g., "2D OV"), and **Hall** (e.g., "Cinema 10").
      * **Store Data:** The findings will be stored in the dictionary, like:
        ```json
        {
          "Mon 24.11": {
            "Wicked: Part 2": [
              "19:30 (Cinema 10, 2D OV)",
              "16:45 (Cinema 10, 2D OmU)"
            ]
          },
          "Tue 25.11": { ... }
        }
        ```
7.  **Format Report:** After the loop finishes, the script will convert this dictionary into a clean, human-readable text message.
8.  **Send Notification:** The script will call the `send_telegram_message()` function, passing this formatted string.

### 5\. Deployment & Scheduling (Coolify)

This is the easiest and most robust hosting method since you already use this stack.

1.  **GitHub Repo:** All code (`scrape_movies.py`, `Dockerfile`, `requirements.txt` for `uv`) will be in your GitHub repository.
2.  **Coolify Setup:**
      * In your Coolify dashboard, go to **Create New Resource \> Scheduled Task**.
      * **Source:** Connect it to your GitHub repository.
      * **Schedule:** Set the cron job schedule (e.g., `0 18 * * 1` for 18:00 every Monday).
      * **Environment Variables:** Add your two Telegram secrets:
          * `TELEGRAM_BOT_TOKEN`
          * `TELEGRAM_CHAT_ID`
3.  **Deploy:** Coolify will automatically build the `Dockerfile` and set up the cron job. It will run on schedule without any further intervention.

### 6\. Project Deliverables

I will provide the following files for you to place in your `uv`-based GitHub repository:

1.  **`scrape_movies.py`:** The complete, production-ready Playwright scraper and Telegram notifier.
2.  **`Dockerfile`:** A multi-stage Dockerfile optimized for Python and Playwright, ensuring a small and secure final image.
3.  **`requirements.txt`:** A list of dependencies for `uv` to install (e.g., `playwright`, `requests`).
4.  **`README.md`:** Instructions on how to set up the Telegram bot and deploy the service to Coolify.
5.  **`.env.example`:** A template file showing the environment variables needed.

-----

### 7\. Action Items: Your Decisions

1.  **How should showtimes be grouped?**

      * Grouped **by day** (cleaner for a "what's on tonight" view).

2.  **What data should be included in the report?**

      * *Default (Recommended):* Title, Time, Hall, and Version (OV/OmU).
      * *Also possible:* Look into the metadata for additional info (e.g., duration, genre) if possible.

3.  **Which delivery method?**

      * (You've already indicated a preference, but please confirm)
      * **Telegram** (Easiest)
      * **Email**
      * **Both**

4.  **Where will you run it?**

      * First test with github actions then
      * **Coolify service on Hetzner VPS**

5.  **When should the schedule run?**

      * *Default:* Every Monday at 20:00 (8:00 PM) CET.
      * *Please provide your preferred time and day.*

6.  **Do you want a JSON file output?**

      * Should the script also save a `schedule.json` file (e.g., in the container or as a build artifact) for other potential uses? (Yes)
