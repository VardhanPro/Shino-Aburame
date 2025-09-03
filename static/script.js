document.addEventListener('DOMContentLoaded', () => {
    // --- DOM ELEMENT SELECTORS ---
    const searchInput = document.getElementById('search-input');
    const searchResultsContainer = document.getElementById('search-results');
    const animeListContainer = document.getElementById('anime-list');
    const messageArea = document.getElementById('message-area');
    const cardTemplate = document.getElementById('anime-card-template');
    const modal = document.getElementById('details-modal');
    const modalCloseBtn = modal.querySelector('.modal-close-btn');
    const themeToggleButton = document.getElementById('theme-toggle');

    // --- THEME SWITCHER LOGIC ---
    const applyTheme = (theme) => {
        if (theme === 'dark') {
            document.body.classList.add('dark-mode');
            document.body.classList.remove('light-mode');
            themeToggleButton.textContent = '☀️';
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.add('light-mode');
            document.body.classList.remove('dark-mode');
            themeToggleButton.textContent = '🌙';
            localStorage.setItem('theme', 'light');
        }
    };

    themeToggleButton.addEventListener('click', () => {
        const newTheme = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
        applyTheme(newTheme);
    });

    // --- Initialize Theme on Load ---
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (savedTheme) {
        applyTheme(savedTheme);
    } else if (prefersDark) {
        applyTheme('dark');
    }


    // --- STATE MANAGEMENT ---
    let searchTimeout;
    let animeDataStore = {};
    initialAnimes.forEach(anime => { animeDataStore[anime.id] = anime; });
    let currentSearchPage = 1;
    let totalSearchResults = 0;

    // --- UTILITY FUNCTIONS ---
    const showMessage = (message, isSuccess) => {
        messageArea.textContent = message;
        messageArea.className = isSuccess ? 'message-success' : 'message-error';
        messageArea.style.display = 'block';
        setTimeout(() => { messageArea.style.display = 'none'; }, 4000);
    };

    // --- DYNAMIC SEARCH & PAGINATION ---
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchResultsContainer.innerHTML = '';
        currentSearchPage = 1;
        const query = searchInput.value.trim();
        if (query.length < 2) return;
        searchTimeout = setTimeout(() => performSearch(query, false), 300);
    });

    const performSearch = async (query, append = false) => {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&page=${currentSearchPage}`);
            const data = await response.json();
            totalSearchResults = data.total;
            displaySearchResults(data.results, append);
        } catch (error) { console.error('Search failed:', error); }
    };

    const displaySearchResults = (results, append = false) => {
        if (!append) searchResultsContainer.innerHTML = '';
        const oldShowMoreBtn = document.getElementById('search-more-btn');
        if (oldShowMoreBtn) oldShowMoreBtn.remove();
        if (results.length === 0 && !append) {
            searchResultsContainer.innerHTML = '<div class="search-result-item">No results found.</div>';
            return;
        }
        results.forEach(anime => {
            const item = document.createElement('div');
            item.className = 'search-result-item';
            item.textContent = anime.title;
            item.dataset.aid = anime.aid;
            item.addEventListener('click', () => addAnime(anime.aid));
            searchResultsContainer.appendChild(item);
        });
        const resultsShown = searchResultsContainer.querySelectorAll('.search-result-item').length;
        if (totalSearchResults > resultsShown) {
            const showMoreBtn = document.createElement('button');
            showMoreBtn.id = 'search-more-btn';
            showMoreBtn.textContent = 'Show More...';
            showMoreBtn.addEventListener('click', () => {
                currentSearchPage++;
                performSearch(searchInput.value.trim(), true);
            });
            searchResultsContainer.appendChild(showMoreBtn);
        }
    };
    
    // --- ADD ANIME TO LIST ---
    const addAnime = async (aid) => {
        searchInput.value = ''; searchResultsContainer.innerHTML = '';
        try {
            const response = await fetch('/api/add', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ aid: aid })
            });
            const result = await response.json();
            if (result.success) {
                renderAnimeCard(result.anime);
                animeDataStore[result.anime.id] = result.anime;
                showMessage('Anime added successfully!', true);
                sortAnimeList();
            } else { showMessage(result.message, false); }
        } catch (error) { showMessage('Failed to add anime.', false); }
    };

    // --- RENDER & UPDATE ANIME CARDS ---
    const renderAnimeCard = (anime) => {
        const cardClone = cardTemplate.content.cloneNode(true);
        const card = cardClone.querySelector('.anime-card');
        card.dataset.id = anime.id;
        card.querySelector('.card-image').src = anime.image_url || 'https://via.placeholder.com/400x225?text=No+Image';
        card.querySelector('.card-title').textContent = anime.title;
        card.querySelector('.card-description').textContent = anime.description;
        card.querySelector('.card-anime-type').textContent = anime.anime_type;
        card.querySelector('.card-episode-count').textContent = `${anime.total_episodes} Episodes`;
        const dates = [anime.start_date, anime.end_date].filter(Boolean).join(' – ');
        card.querySelector('.dates').textContent = dates;
        
        animeListContainer.appendChild(cardClone);
        
        const newCardInDom = animeListContainer.querySelector(`.anime-card[data-id='${anime.id}']`);
        updateCardProgress(newCardInDom, anime.watched_episodes, anime.total_episodes);
    };

    const updateCardProgress = (card, watched, total) => {
        const progressBar = card.querySelector('.progress-bar');
        const progressText = card.querySelector('.progress-text');
        const episodeText = card.querySelector('.card-progress-episodes');
        const percentage = total > 0 ? Math.floor((watched / total) * 100) : 0;
        
        progressBar.value = watched;
        progressBar.max = total;
        progressText.textContent = `${percentage}%`;
        episodeText.textContent = `${watched} / ${total}`;

        if (total > 0 && percentage >= 100) {
            card.classList.add('is-completed');
        } else {
            card.classList.remove('is-completed');
        }
    };

    // --- SORTING ---
    const sortAnimeList = () => {
        const cards = Array.from(animeListContainer.querySelectorAll('.anime-card'));
        cards.sort((a, b) => {
            const aData = animeDataStore[a.dataset.id];
            const bData = animeDataStore[b.dataset.id];
            const aIsCompleted = aData.watched_episodes >= aData.total_episodes && aData.total_episodes > 0;
            const bIsCompleted = bData.watched_episodes >= bData.total_episodes && bData.total_episodes > 0;
            if (aIsCompleted && !bIsCompleted) return 1;
            if (!aIsCompleted && bIsCompleted) return -1;
            return aData.title.localeCompare(bData.title);
        });
        cards.forEach(card => animeListContainer.appendChild(card));
    };

    // --- EVENT LISTENERS FOR CARD ACTIONS ---
    animeListContainer.addEventListener('click', (e) => {
        const card = e.target.closest('.anime-card');
        if (!card) return;
        const animeId = card.dataset.id;
        if (e.target.closest('.card-actions')) {
            if (e.target.matches('.remove-btn')) {
                if (confirm('Are you sure you want to remove this anime?')) {
                    fetch(`/api/remove/${animeId}`, { method: 'DELETE' })
                        .then(res => res.json())
                        .then(result => {
                            if (result.success) {
                                card.remove();
                                delete animeDataStore[animeId];
                                showMessage('Anime removed.', true);
                            }
                        });
                }
            }
        } else { openModal(animeId); }
    });

    // --- PRESS AND HOLD LOGIC ---
    let pressTimer, pressInterval;
    const updateEpisode = async (animeId, action) => {
        const card = animeListContainer.querySelector(`.anime-card[data-id='${animeId}']`);
        const response = await fetch(`/api/update/${animeId}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action })
        });
        const result = await response.json();
        if (result.success) {
            const anime = animeDataStore[animeId];
            const wasCompleted = anime.watched_episodes >= anime.total_episodes && anime.total_episodes > 0;
            anime.watched_episodes = result.watched_episodes;
            const isCompleted = anime.watched_episodes >= anime.total_episodes && anime.total_episodes > 0;
            updateCardProgress(card, anime.watched_episodes, anime.total_episodes);
            if (wasCompleted !== isCompleted) {
                sortAnimeList();
            }
        }
    };
    animeListContainer.addEventListener('mousedown', (e) => {
        if (!e.target.matches('.increment-btn, .decrement-btn')) return;
        const card = e.target.closest('.anime-card');
        const animeId = card.dataset.id;
        const action = e.target.matches('.increment-btn') ? 'increment' : 'decrement';
        updateEpisode(animeId, action);
        pressTimer = setTimeout(() => {
            pressInterval = setInterval(() => updateEpisode(animeId, action), 100);
        }, 500);
    });
    const stopPress = () => { clearTimeout(pressTimer); clearInterval(pressInterval); };
    animeListContainer.addEventListener('mouseup', stopPress);
    animeListContainer.addEventListener('mouseleave', stopPress, true);

    // --- MODAL LOGIC ---
    const openModal = (animeId) => {
        const anime = animeDataStore[animeId];
        if (!anime) return;
        modal.querySelector('#modal-img').src = anime.image_url || 'https://via.placeholder.com/400x225?text=No+Image';
        modal.querySelector('#modal-title').textContent = anime.title;
        modal.querySelector('#modal-meta').innerHTML = `<span>${anime.anime_type}</span> | <span>${[anime.start_date, anime.end_date].filter(Boolean).join(' – ')}</span>`;
        modal.querySelector('#modal-description').innerHTML = anime.description;
        modal.style.display = 'flex';
    };
    const closeModal = () => { modal.style.display = 'none'; };
    modalCloseBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    // --- INITIAL LOAD ---
    const renderInitialList = (animes) => {
        let index = 0;
        function renderNext() {
            if (index >= animes.length) return;
            renderAnimeCard(animes[index]);
            index++;
            requestAnimationFrame(renderNext);
        }
        renderNext();
    };
    renderInitialList(initialAnimes);
});