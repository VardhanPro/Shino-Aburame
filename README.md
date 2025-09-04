# Shino Aburame - Anime Tracker 🍃

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Shino Aburame is a powerful, self-hosted anime tracker that helps you meticulously monitor your viewing progress. It uses a local cache of the AniDB database for lightning-fast searches and provides a dynamic, modern web interface to manage your list.


---

## ✨ Features

* **⚡ Fast Local Search:** Search the entire AniDB catalog instantly thanks to a local database cache.
* **🔍 Live Search Results:** Get search results dynamically as you type.
* **📖 Detailed Anime Cards:** View cover art, descriptions, episode counts, and airing dates for each anime.
* **📊 Progress Tracking:** Easily track watched episodes with a visual progress bar.
* **👆 Advanced Controls:** "Press and Hold" the `+` and `-` buttons to update episode counts quickly.
* **✅ Smart Sorting:** Completed anime are automatically sorted to the bottom of your list.
* **🖼️ Details Modal:** Click on any card to view a larger poster and the full, unabridged description.
* **📱 Responsive Design:** A clean, modern interface that works on both desktop and mobile devices.
* **🔒 Secure & Private:** Your tracking data is stored locally in a private SQLite database. All API calls are cached and rate-limited to be respectful of the AniDB API.

---

## 🛠️ Technology Stack

* **Backend:** Python with Flask
* **Database:** SQLite for both the local AniDB cache and the user's tracking data
* **API:** [AniDB.net](http://anidb.net) HTTP API (for fetching details)
* **Frontend:** HTML, CSS, and modern JavaScript (no frameworks)

---

## 🚀 Getting Started

Follow these instructions to get a local copy up and running.

### Prerequisites

* **Git:** To clone the repository.
* **Python 3.8+** and **pip**: To run the backend application.

### Installation & Setup

1.  **Clone the repository to your local machine:**
    ```sh
    git clone https://github.com/VardhanPro/Shino-Aburame.git
    cd Shino-Aburame
    ```

2.  **Create and activate a virtual environment:**
    * On Windows:
        ```sh
        python -m venv venv
        venv\Scripts\activate
        ```
    * On macOS / Linux:
        ```sh
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install the required Python packages:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Create your environment file:**
    * Create a new file named `.env` in the project's root directory.
    * Add your AniDB client name to it like so:
        ```ini
        ANIDB_CLIENT="animetrackerash"
        ANIDB_CLIENT_VERSION="1"
        ```

5.  **Build the local AniDB title cache:**
    * This is a one-time setup step that downloads the entire AniDB title database. **This may take several minutes.**
    ```sh
    python update_anidb_cache.py
    ```

6.  **Initialize your personal tracker database:**
    * This one-time step creates the `tracker.db` file where your list will be stored.
    ```sh
    python init_db.py
    ```

---

## 🏃 Running the Application

1.  **Start the Flask server:**
    ```sh
    python app.py
    ```

2.  **Open the tracker in your browser:**
    * Navigate to **http://127.0.0.1:5000**

---

## 📖 How to Use

* **Search:** Start typing the name of an anime in the search bar. Results will appear after you type at least two characters.
* **Add:** Click on an anime from the search results to add it to your tracking list.
* **Update Progress:** Use the **`+`** and **`-`** buttons on a card to update your watched episode count. You can click or press-and-hold for rapid updates.
* **View Details:** Click anywhere on an anime card (except the action buttons) to open a modal with the full description and a larger poster.
* **Remove:** Click the trash can icon (🗑️) to permanently remove an anime from your list.

---

## 📜 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
