// Elements DOM
const loginContainer = document.getElementById('login-container');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const playerContainer = document.getElementById('player-container');
const playerNicknameHeader = document.getElementById('player-nickname-header');
const playerPersonPhoto = document.getElementById('player-person-photo');
const playerPersonPhotoContainer = document.getElementById('player-person-photo-container');
// Compatibilité - ces éléments peuvent ne plus être dans le DOM
const playerFeetPhoto = document.getElementById('player-feet-photo'); 
const playerFeetPhotoContainer = null; // N'est plus dans le nouveau design
const targetNickname = document.getElementById('target-nickname');
const targetAction = document.getElementById('target-action');
const targetPersonPhoto = document.getElementById('target-person-photo');
const targetPersonPhotoContainer = document.getElementById('target-person-photo-container');
const targetInfoSection = document.getElementById('target-info-section');
const actionButtons = document.querySelector('.action-buttons');
// Éléments pour la modale
const photoModal = document.getElementById('photo-modal');
const modalImage = document.getElementById('modal-image');
const closeModal = document.getElementById('close-modal');
const targetCard = document.getElementById('target-card');
const noTargetMessage = document.getElementById('no-target-message');
const killedBtn = document.getElementById('killed-btn');
const giveUpBtn = document.getElementById('give-up-btn');
const logoutBtn = document.getElementById('logout-btn');
const killNotification = document.getElementById('kill-notification');
const newTargetNickname = document.getElementById('new-target-nickname');
const newTargetAction = document.getElementById('new-target-action');
const newTargetPersonPhoto = document.getElementById('new-target-person-photo');
const newTargetPersonPhotoContainer = document.getElementById('new-target-person-photo-container');
const closeNotification = document.getElementById('close-notification');
const trombiSection = document.getElementById('trombi-section');
const trombiList = document.getElementById('trombi-list');
const trombiDetails = document.getElementById('trombi-details');
const trombiEmpty = document.getElementById('trombi-empty');
const trombiError = document.getElementById('trombi-error');
const adminOverviewSection = document.getElementById('admin-overview');
const adminOverviewBody = document.getElementById('admin-overview-body');
const adminOverviewEmpty = document.getElementById('admin-overview-empty');
const adminOverviewError = document.getElementById('admin-overview-error');
const adminRefreshBtn = document.getElementById('admin-refresh');
const deadPlayerInfo = document.getElementById('dead-player-info');
const aliveCountMessage = document.getElementById('alive-count-message');
const podiumSection = document.getElementById('podium-section');
const gameOverMessage = document.getElementById('game-over-message');
const leaderboardSection = document.getElementById('leaderboard-section');
const leaderboardList = document.getElementById('leaderboard-list');
const leaderboardEmpty = document.getElementById('leaderboard-empty');

let trombiIntervalId = null;
let currentPlayerNickname = null;
let trombiPlayers = [];
let currentTrombiSelection = null;
let viewerCanSeeStatus = false;
let viewerStatus = 'alive';
let adminOverviewIntervalId = null;
let currentPlayerIsAdmin = false;
let adminOverviewData = [];
let adminOverviewSort = { column: null, direction: 'asc' };
let adminSortHeaders = [];
let currentTrombiCategory = 'all';
let currentAdminCategory = 'all';

// Sons de pet disponibles
const petSounds = [
    './client/sounds/pet1.mp3',
    './client/sounds/pet2.mp3',
    './client/sounds/pet3.mp3',
    './client/sounds/pet4.mp3',
    './client/sounds/pet5.mp3',
    './client/sounds/pet6.mp3',
    './client/sounds/pet7.mp3'
];

/**
 * Joue un son de pet aléatoire
 */
function playRandomPetSound() {
    const randomIndex = Math.floor(Math.random() * petSounds.length);
    const sound = new Audio(petSounds[randomIndex]);
    sound.play();
}

function getDriveImageUrl(fileId, size = 600) {
    if (!fileId || typeof fileId !== 'string') {
        return '';
    }
    const trimmedId = fileId.trim();
    if (!trimmedId) {
        return '';
    }
    const encodedId = encodeURIComponent(trimmedId);
    const cacheBuster = Math.floor(Date.now() / 60000);
    const sizeParam = Number.isFinite(size) && size > 0 ? `&sz=w${Math.round(size)}` : '';
    return `https://drive.google.com/thumbnail?id=${encodedId}${sizeParam}&cache=${cacheBuster}`;
}

// Fonction pour ouvrir la modal avec une image
function openPhotoModal(imageSrc) {
    if (!modalImage || !photoModal) {
        console.error("Les éléments de la modale n'existent pas");
        return;
    }
    
    if (!imageSrc) {
        console.error("Source de l'image invalide");
        return;
    }
    
    try {
        modalImage.src = imageSrc;
        photoModal.classList.remove('hidden');
    } catch (error) {
        console.error("Erreur lors de l'ouverture de la modale:", error);
    }
}

// Fonction pour fermer la modal
function closePhotoModal() {
    if (photoModal) {
        photoModal.classList.add('hidden');
    }
}

function startTrombiUpdates() {
    loadTrombi();
    loadPodium();
    loadLeaderboard();
    if (trombiIntervalId) {
        clearInterval(trombiIntervalId);
    }
    trombiIntervalId = setInterval(() => {
        loadTrombi();
        loadPodium();
        loadLeaderboard();
    }, 30000);
}

function stopTrombiUpdates() {
    if (trombiIntervalId) {
        clearInterval(trombiIntervalId);
        trombiIntervalId = null;
    }
}

function resetTrombiDisplay() {
    trombiPlayers = [];
    currentTrombiSelection = null;
    viewerCanSeeStatus = false;
    viewerStatus = 'alive';
    if (trombiList) {
        trombiList.innerHTML = '';
    }
    if (trombiDetails) {
        trombiDetails.innerHTML = '<p class="trombi-placeholder">Sélectionne un joueur pour découvrir son profil.</p>';
    }
    if (trombiEmpty) {
        trombiEmpty.classList.add('hidden');
    }
    if (trombiError) {
        trombiError.classList.add('hidden');
    }
}

function startAdminOverviewUpdates() {
    loadAdminOverview();
    if (adminOverviewIntervalId) {
        clearInterval(adminOverviewIntervalId);
    }
    adminOverviewIntervalId = setInterval(loadAdminOverview, 30000);
}

function stopAdminOverviewUpdates() {
    if (adminOverviewIntervalId) {
        clearInterval(adminOverviewIntervalId);
        adminOverviewIntervalId = null;
    }
}

function resetAdminOverviewDisplay() {
    if (adminOverviewBody) {
        adminOverviewBody.innerHTML = '';
    }
    if (adminOverviewEmpty) {
        adminOverviewEmpty.classList.add('hidden');
    }
    if (adminOverviewError) {
        adminOverviewError.classList.add('hidden');
    }
    adminOverviewData = [];
    adminOverviewSort = { column: null, direction: 'asc' };
    currentAdminCategory = 'all';
    
    // Réinitialiser les boutons de catégorie
    const adminCategoryButtons = document.querySelectorAll('.admin-category-btn');
    adminCategoryButtons.forEach(btn => {
        if (btn.dataset.adminCategory === 'all') {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    updateAdminSortIndicators();
}

function loadTrombi() {
    if (!trombiList) {
        return;
    }

    if (trombiError) {
        trombiError.classList.add('hidden');
    }

    fetch('/api/trombi')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data || !data.success || !Array.isArray(data.players)) {
                throw new Error('Format de réponse invalide');
            }

            viewerCanSeeStatus = Boolean(data.viewer && data.viewer.can_view_status);
            if (data.viewer && typeof data.viewer.status === 'string') {
                viewerStatus = data.viewer.status;
            }

            trombiPlayers = data.players
                .map(player => {
                    const nickname = typeof player.nickname === 'string' ? player.nickname.trim() : '';
                    return {
                        ...player,
                        nickname,
                    };
                });

            trombiPlayers.sort((a, b) => {
                const adminA = Boolean(a && a.is_admin);
                const adminB = Boolean(b && b.is_admin);
                if (adminA !== adminB) {
                    return adminA ? -1 : 1;
                }
                const nameA = (a && a.nickname ? a.nickname : '').toLowerCase();
                const nameB = (b && b.nickname ? b.nickname : '').toLowerCase();
                return nameA.localeCompare(nameB, 'fr', { sensitivity: 'base', ignorePunctuation: true });
            });
            updateTrombiCategoryButtons();
            updateDeadPlayerInfo();
            renderTrombi();
        })
        .catch(error => {
            console.error('Erreur lors du chargement du trombinoscope:', error);
            if (trombiError) {
                trombiError.classList.remove('hidden');
            }
            if (trombiEmpty) {
                trombiEmpty.classList.add('hidden');
            }
        });
}

function updateTrombiCategoryButtons() {
    const categoryButtons = document.querySelectorAll('.trombi-category-btn');
    
    categoryButtons.forEach(btn => {
        const category = btn.dataset.category;
        
        // Désactiver "Vivants" et "Morts" pour tous les joueurs non-admin
        // Seuls les admins peuvent voir ces catégories
        if ((category === 'alive' || category === 'dead') && !currentPlayerIsAdmin) {
            btn.disabled = true;
            btn.classList.add('disabled');
        } else {
            btn.disabled = false;
            btn.classList.remove('disabled');
        }
    });
}

function updateDeadPlayerInfo() {
    if (!deadPlayerInfo || !aliveCountMessage) return;
    
    const isDead = viewerStatus === 'dead' || viewerStatus === 'gaveup';
    
    if (isDead && trombiPlayers) {
        // Compter les joueurs vivants
        const aliveCount = trombiPlayers.filter(p => p.status === 'alive').length;
        
        // Cacher le message si le jeu est terminé (1 joueur ou moins)
        if (aliveCount <= 1) {
            deadPlayerInfo.classList.add('hidden');
        } else {
            aliveCountMessage.textContent = `Il ne reste plus que ${aliveCount} joueur${aliveCount > 1 ? 's' : ''} en vie`;
            deadPlayerInfo.classList.remove('hidden');
        }
    } else {
        deadPlayerInfo.classList.add('hidden');
    }
}

function renderTrombi() {
    if (!trombiList) {
        return;
    }

    trombiList.innerHTML = '';

    if (!Array.isArray(trombiPlayers) || trombiPlayers.length === 0) {
        if (trombiEmpty) {
            trombiEmpty.classList.remove('hidden');
        }
        if (trombiDetails) {
            trombiDetails.innerHTML = '<p class="trombi-placeholder">Pas encore de joueurs à afficher.</p>';
        }
        return;
    }

    if (trombiEmpty) {
        trombiEmpty.classList.add('hidden');
    }

    // Filtrer selon la catégorie sélectionnée
    const filteredPlayers = trombiPlayers.filter(player => {
        if (currentTrombiCategory === 'all') {
            return true;
        } else if (currentTrombiCategory === 'alive') {
            const status = (player.status || 'alive').toLowerCase();
            return status === 'alive';
        } else if (currentTrombiCategory === 'dead') {
            const status = (player.status || 'alive').toLowerCase();
            return status === 'dead';
        } else if (currentTrombiCategory === 'admin') {
            return player.is_admin === true;
        }
        return true;
    });

    if (filteredPlayers.length === 0) {
        if (trombiEmpty) {
            trombiEmpty.classList.remove('hidden');
        }
        if (trombiDetails) {
            trombiDetails.innerHTML = '<p class="trombi-placeholder">Aucun joueur dans cette catégorie.</p>';
        }
        return;
    }

    const currentSelectionName = currentTrombiSelection && currentTrombiSelection.toLowerCase();

    filteredPlayers.forEach(player => {
        const entryButton = document.createElement('button');
        entryButton.type = 'button';
        entryButton.classList.add('trombi-entry');

        const nickname = (player.nickname || '???').trim();
        entryButton.dataset.nickname = nickname;

        const labelWrapper = document.createElement('span');
        labelWrapper.classList.add('trombi-entry-label');

        const nameSpan = document.createElement('span');
        nameSpan.classList.add('trombi-entry-name');
        nameSpan.textContent = nickname || '???';
        labelWrapper.appendChild(nameSpan);

        if (player.year) {
            const yearBadge = document.createElement('span');
            yearBadge.classList.add('trombi-year-badge');
            yearBadge.textContent = player.year;
            labelWrapper.appendChild(yearBadge);
        }

        if (player.is_admin) {
            labelWrapper.appendChild(createAdminBadge());
        }

        entryButton.appendChild(labelWrapper);

        if (currentPlayerNickname && nickname && nickname.toLowerCase() === currentPlayerNickname.toLowerCase()) {
            entryButton.classList.add('trombi-entry-self');
        }

        if (currentSelectionName && nickname.toLowerCase() === currentSelectionName) {
            entryButton.classList.add('selected');
        }

        // Seuls les admins peuvent voir les statuts vivant/mort dans le trombinoscope
        if (currentPlayerIsAdmin && typeof player.status === 'string' && player.status) {
            const statusChip = document.createElement('span');
            const normalizedStatus = player.status.toLowerCase();
            statusChip.classList.add('status-pill', `status-${normalizedStatus}`);
            statusChip.textContent = getStatusLabel(normalizedStatus);
            entryButton.appendChild(statusChip);
        }

        entryButton.addEventListener('click', () => {
            selectTrombiEntry(nickname);
        });

        trombiList.appendChild(entryButton);
    });

    if (!currentTrombiSelection && filteredPlayers.length > 0) {
        selectTrombiEntry(filteredPlayers[0].nickname || '');
    } else if (currentTrombiSelection) {
        const isCurrentInFiltered = filteredPlayers.some(p => 
            (p.nickname || '').trim().toLowerCase() === currentTrombiSelection.toLowerCase()
        );
        if (isCurrentInFiltered) {
            selectTrombiEntry(currentTrombiSelection);
        } else if (filteredPlayers.length > 0) {
            selectTrombiEntry(filteredPlayers[0].nickname || '');
        }
    }
}

function selectTrombiEntry(nickname) {
    const normalizedNickname = (nickname || '').trim();

    if (!normalizedNickname) {
        return;
    }

    currentTrombiSelection = normalizedNickname;

    if (trombiList) {
        Array.from(trombiList.children).forEach(child => {
            if (!child.dataset) {
                return;
            }
            const childNickname = (child.dataset.nickname || '').trim().toLowerCase();
            if (childNickname === normalizedNickname.toLowerCase()) {
                child.classList.add('selected');
            } else {
                child.classList.remove('selected');
            }
        });
    }

    const player = trombiPlayers.find(entry => (entry.nickname || '').trim().toLowerCase() === normalizedNickname.toLowerCase());
    renderTrombiDetails(player);
}

function renderTrombiDetails(player) {
    if (!trombiDetails) {
        return;
    }

    trombiDetails.innerHTML = '';

    if (!player) {
        trombiDetails.innerHTML = '<p class="trombi-placeholder">Impossible de charger ce profil.</p>';
        return;
    }

    const title = document.createElement('h3');
    title.classList.add('trombi-name-display');

    const displayName = (player.nickname || '???').trim() || '???';

    const titleName = document.createElement('span');
    titleName.classList.add('trombi-entry-name');
    titleName.textContent = displayName;
    title.appendChild(titleName);

    if (player.year) {
        const yearBadge = document.createElement('span');
        yearBadge.classList.add('trombi-year-badge');
        yearBadge.textContent = player.year;
        title.appendChild(yearBadge);
    }

    if (player.is_admin) {
        title.appendChild(createAdminBadge());
    }

    trombiDetails.appendChild(title);

    // Afficher le numéro de téléphone pour les admins
    if (player.is_admin && player.phone) {
        const phoneContainer = document.createElement('p');
        phoneContainer.classList.add('trombi-phone');
        
        const phoneLink = document.createElement('a');
        phoneLink.href = `tel:${player.phone}`;
        phoneLink.textContent = `📞 ${player.phone}`;
        phoneLink.title = 'Appeler ce numéro';
        
        phoneContainer.appendChild(phoneLink);
        trombiDetails.appendChild(phoneContainer);
    }

    const metaContainer = document.createElement('div');
    metaContainer.classList.add('trombi-meta');
    let metaHasContent = false;

    // Seuls les admins peuvent voir les statuts vivant/mort dans le trombinoscope
    if (currentPlayerIsAdmin && typeof player.status === 'string' && player.status) {
        const statusBadge = document.createElement('span');
        const normalizedStatus = player.status.toLowerCase();
        statusBadge.classList.add('status-pill', `status-${normalizedStatus}`);
        statusBadge.textContent = getStatusLabel(normalizedStatus);
        statusBadge.setAttribute('aria-label', `Statut: ${getStatusLabel(normalizedStatus)}`);
        metaContainer.appendChild(statusBadge);
        metaHasContent = true;
    }

    const hasFeetPhoto = typeof player.feet_photo === 'string' && player.feet_photo.trim().length > 0;
    if (hasFeetPhoto) {
        const feetButton = document.createElement('button');
        feetButton.type = 'button';
    feetButton.classList.add('trombi-feet-button', 'btn', 'btn-secondary');
        feetButton.textContent = 'voir ses pieds';
        feetButton.addEventListener('click', () => {
            const feetUrl = getDriveImageUrl(player.feet_photo, 600);
            if (feetUrl) {
                openPhotoModal(feetUrl);
            }
        });
        metaContainer.appendChild(feetButton);
        metaHasContent = true;
    }

    if (metaHasContent) {
        trombiDetails.appendChild(metaContainer);
    }

    const photoContainer = document.createElement('div');
    photoContainer.classList.add('trombi-photo-container');

    if (player.person_photo) {
        const photo = document.createElement('img');
        photo.classList.add('trombi-photo');
        photo.src = getDriveImageUrl(player.person_photo, 600);
        photo.alt = `Photo de ${displayName}`;
        photo.loading = 'lazy';
        photo.addEventListener('click', () => openPhotoModal(photo.src));
        
        // Détecter les erreurs de chargement (permissions Drive manquantes)
        photo.addEventListener('error', () => {
            photoContainer.innerHTML = '';
            const errorMsg = document.createElement('p');
            errorMsg.classList.add('trombi-placeholder', 'trombi-photo-error');
            errorMsg.textContent = '⚠️ Photo inaccessible (permissions Google Drive manquantes)';
            errorMsg.title = 'Cette photo nécessite une authentification Google. Demandez au propriétaire de la rendre publique.';
            photoContainer.appendChild(errorMsg);
        });
        
        photoContainer.appendChild(photo);
    } else {
        const placeholder = document.createElement('p');
        placeholder.classList.add('trombi-placeholder');
        placeholder.textContent = 'Pas de photo disponible pour ce joueur.';
        photoContainer.appendChild(placeholder);
    }

    trombiDetails.appendChild(photoContainer);

    // Afficher le message personnalisé basé sur les réponses du joueur
    if (player.before_answer || player.kro_answer) {
        const info = document.createElement('p');
        info.classList.add('trombi-status-info');
        
        let message = '';
        
        // Message basé sur "Est-ce que c'était mieux avant ?"
        const beforeAnswer = (player.before_answer || '').toLowerCase().trim();
        if (beforeAnswer === 'oui' || beforeAnswer === 'yes') {
            message = 'Ce joueur est sénile';
        } else if (beforeAnswer) {
            message = 'Ce fyot pense que c\'était pas mieux avant';
        }
        
        // Ajouter la réponse sur les quarts dans une krô
        const kroAnswer = (player.kro_answer || '').trim();
        if (kroAnswer) {
            if (message) {
                message += ' et pense qu\'il y a ';
            } else {
                message = 'Ce joueur pense qu\'il y a ';
            }
            
            // Si la réponse contient "Réponse B", ajouter "(gros fyot)"
            if (kroAnswer.toLowerCase().includes('réponse b') || kroAnswer.toLowerCase().includes('reponse b')) {
                message += `${kroAnswer} quarts dans une krô (gros fyot)`;
            } else {
                message += `${kroAnswer} quarts dans une krô`;
            }
        }
        
        if (message) {
            info.textContent = message;
            trombiDetails.appendChild(info);
        }
    }
}

function loadAdminOverview() {
    if (!adminOverviewBody || !currentPlayerIsAdmin) {
        return;
    }

    if (adminOverviewError) {
        adminOverviewError.classList.add('hidden');
    }

    fetch('/api/admin/overview')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data || !data.success || !Array.isArray(data.players)) {
                throw new Error('Format de réponse invalide');
            }
            adminOverviewData = data.players.slice();
            applyAdminSortAndRender();
        })
        .catch(error => {
            console.error('Erreur lors du chargement de la vue admin:', error);
            if (adminOverviewError) {
                adminOverviewError.classList.remove('hidden');
            }
        });
}

function applyAdminSortAndRender() {
    if (!Array.isArray(adminOverviewData)) {
        adminOverviewData = [];
    }

    const playersToRender = adminOverviewData.slice();
    const { column, direction } = adminOverviewSort;

    if (column) {
        playersToRender.sort((a, b) => {
            const valueA = getAdminSortValue(a, column);
            const valueB = getAdminSortValue(b, column);
            const comparison = valueA.localeCompare(valueB, 'fr', { sensitivity: 'base', ignorePunctuation: true });
            if (comparison === 0) {
                return 0;
            }
            return direction === 'desc' ? -comparison : comparison;
        });
    }

    renderAdminOverview(playersToRender);
}

function getAdminSortValue(player, columnKey) {
    if (!player || !columnKey) {
        return '';
    }
    const rawValue = player[columnKey];
    if (typeof rawValue === 'number') {
        return rawValue.toString();
    }
    if (typeof rawValue === 'string') {
        return rawValue.trim().toLowerCase();
    }
    return '';
}

function handleAdminSort(columnKey) {
    if (!columnKey) {
        return;
    }

    if (adminOverviewSort.column === columnKey) {
        adminOverviewSort = {
            column: columnKey,
            direction: adminOverviewSort.direction === 'asc' ? 'desc' : 'asc'
        };
    } else {
        adminOverviewSort = { column: columnKey, direction: 'asc' };
    }

    if (!Array.isArray(adminOverviewData) || adminOverviewData.length === 0) {
        updateAdminSortIndicators();
        return;
    }

    applyAdminSortAndRender();
}

function updateAdminSortIndicators() {
    if (!Array.isArray(adminSortHeaders) || adminSortHeaders.length === 0) {
        return;
    }

    adminSortHeaders.forEach(header => {
        if (!header || !header.dataset) {
            return;
        }
        const headerKey = header.dataset.sortKey;
        if (adminOverviewSort.column === headerKey) {
            header.dataset.sortDirection = adminOverviewSort.direction;
        } else {
            header.removeAttribute('data-sort-direction');
        }
    });
}

function renderAdminOverview(players) {
    if (!adminOverviewBody) {
        return;
    }

    updateAdminSortIndicators();

    adminOverviewBody.innerHTML = '';

    if (!players || players.length === 0) {
        if (adminOverviewEmpty) {
            adminOverviewEmpty.classList.remove('hidden');
        }
        return;
    }

    if (adminOverviewEmpty) {
        adminOverviewEmpty.classList.add('hidden');
    }

    // Filtrer les joueurs selon la catégorie sélectionnée
    const filteredPlayers = players.filter(player => {
        if (currentAdminCategory === 'all') {
            return true;
        }
        const rawStatus = typeof player.status === 'string' ? player.status.trim().toLowerCase() : '';
        return rawStatus === currentAdminCategory;
    });

    // Si aucun joueur après filtrage, afficher le message vide
    if (filteredPlayers.length === 0) {
        if (adminOverviewEmpty) {
            adminOverviewEmpty.classList.remove('hidden');
        }
        return;
    }

    filteredPlayers.forEach(player => {
        const row = document.createElement('tr');

        const rawStatus = typeof player.status === 'string' ? player.status.trim().toLowerCase() : '';
        const knownStatuses = ['alive', 'dead', 'gaveup'];
        const statusKey = knownStatuses.includes(rawStatus) ? rawStatus : 'unknown';

        if (statusKey !== 'unknown') {
            row.classList.add('admin-row-status', `admin-row-status-${statusKey}`);
        }

        const nicknameCell = document.createElement('td');
        const baseName = (player.nickname || '???').trim() || '???';
        nicknameCell.textContent = baseName;
        if (player.is_admin) {
            const adminHint = document.createElement('span');
            adminHint.classList.add('admin-inline-label');
            adminHint.textContent = ' (admin)';
            nicknameCell.appendChild(adminHint);
        }

        const statusCell = document.createElement('td');
        if (statusKey !== 'unknown') {
            const statusBadge = document.createElement('span');
            statusBadge.classList.add('status-pill', `status-${statusKey}`, 'admin-status-pill');
            statusBadge.textContent = getStatusLabel(statusKey);
            statusCell.appendChild(statusBadge);
        } else {
            statusCell.textContent = player.status || 'Inconnu';
        }

        const targetCell = document.createElement('td');
        targetCell.textContent = player.target || '—';

        const actionCell = document.createElement('td');
        actionCell.textContent = player.action || '—';

        const initialTargetCell = document.createElement('td');
        initialTargetCell.textContent = player.initial_target || '—';

        const initialActionCell = document.createElement('td');
        initialActionCell.textContent = player.initial_action || '—';

        row.appendChild(nicknameCell);
        row.appendChild(statusCell);
        row.appendChild(targetCell);
        row.appendChild(actionCell);
        row.appendChild(initialTargetCell);
        row.appendChild(initialActionCell);

        adminOverviewBody.appendChild(row);
    });
}

function createAdminBadge() {
    const badge = document.createElement('span');
    badge.classList.add('trombi-admin-tag');
    badge.textContent = '(Admin)';
    badge.setAttribute('aria-label', 'Administrateur');
    return badge;
}

function getStatusLabel(status) {
    switch (status) {
        case 'dead':
            return 'Mort';
        case 'gaveup':
            return 'Abandon';
        case 'alive':
        default:
            return 'Vivant';
    }
}

/**
 * Charge et affiche le podium si le jeu est terminé
 */
function loadPodium() {
    if (!podiumSection) {
        return;
    }

    fetch('/api/podium')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data || !data.success) {
                throw new Error('Format de réponse invalide');
            }

            if (data.game_over && data.podium && data.podium.length > 0) {
                renderPodium(data.podium);
                podiumSection.classList.remove('hidden');
                // Afficher le message de fin de jeu
                if (gameOverMessage) {
                    gameOverMessage.classList.remove('hidden');
                }
                // Cacher la section cible, le message mort et les boutons d'action si le jeu est terminé
                if (targetInfoSection) {
                    targetInfoSection.classList.add('hidden');
                }
                if (deadPlayerInfo) {
                    deadPlayerInfo.classList.add('hidden');
                }
                if (actionButtons) {
                    actionButtons.classList.add('hidden');
                }
            } else {
                podiumSection.classList.add('hidden');
                // Cacher le message de fin de jeu
                if (gameOverMessage) {
                    gameOverMessage.classList.add('hidden');
                }
                // Afficher la section cible si le jeu continue (sauf si le joueur est mort)
                if (targetInfoSection && viewerStatus === 'alive') {
                    targetInfoSection.classList.remove('hidden');
                }
                // Afficher les boutons d'action si le joueur est vivant
                if (actionButtons && viewerStatus === 'alive') {
                    actionButtons.classList.remove('hidden');
                }
                // Mettre à jour l'affichage du message mort
                updateDeadPlayerInfo();
            }
        })
        .catch(error => {
            console.error('Erreur lors du chargement du podium:', error);
            podiumSection.classList.add('hidden');
        });
}

/**
 * Affiche le podium des vainqueurs
 */
function renderPodium(podium) {
    if (!podiumSection) {
        return;
    }

    podium.forEach(player => {
        const placeElement = document.getElementById(`podium-place-${player.rank}`);
        if (!placeElement) return;

        const photoElement = placeElement.querySelector('.podium-photo');
        const nameElement = placeElement.querySelector('.podium-name');
        const yearElement = placeElement.querySelector('.podium-year');

        if (photoElement && player.person_photo) {
            const photoUrl = getDriveImageUrl(player.person_photo, 300);
            photoElement.src = photoUrl;
            photoElement.alt = `Photo de ${player.nickname}`;
            
            // Rendre la photo cliquable pour l'agrandir
            photoElement.onclick = () => openPhotoModal(photoUrl);
            
            // Gérer les erreurs de chargement
            photoElement.onerror = () => {
                photoElement.src = '';
                photoElement.alt = 'Photo non disponible';
            };
        }

        if (nameElement) {
            const kills = player.kill_count || 0;
            nameElement.textContent = `${player.nickname || '???'} (${kills} kill${kills > 1 ? 's' : ''})`;
        }

        if (yearElement && player.year) {
            yearElement.textContent = player.year;
        }
    });
}

/**
 * Charge le podium des meilleurs killers
 */
// Charger le leaderboard permanent des tueurs
async function loadLeaderboard() {
    try {
        const response = await fetch('/api/leaderboard', {
            method: 'GET',
            credentials: 'include'
        });

        if (!response.ok) {
            console.error('Erreur lors du chargement du leaderboard:', response.status);
            return;
        }

        const data = await response.json();
        
        // Filtrer les joueurs avec au moins 1 kill
        const playersWithKills = (data.leaderboard || []).filter(player => (player.kill_count || 0) > 0);
        
        if (playersWithKills.length === 0) {
            // Afficher le message "Soit le premier à faire un kill !"
            if (leaderboardList) leaderboardList.classList.add('hidden');
            if (leaderboardEmpty) leaderboardEmpty.classList.remove('hidden');
        } else {
            // Afficher le leaderboard
            if (leaderboardEmpty) leaderboardEmpty.classList.add('hidden');
            if (leaderboardList) leaderboardList.classList.remove('hidden');
            renderLeaderboard(playersWithKills);
        }
    } catch (error) {
        console.error('Erreur lors du chargement du leaderboard:', error);
    }
}

// Afficher le leaderboard
function renderLeaderboard(players) {
    leaderboardList.innerHTML = '';
    
    // Grouper les joueurs par nombre de kills (valeurs uniques triées)
    const killCounts = [...new Set(players.map(p => p.kill_count || 0))].sort((a, b) => b - a);
    
    // Attribuer les médailles selon les groupes de kills
    // 1er groupe (plus de kills) = Or, 2ème groupe = Argent, 3ème groupe = Bronze
    const getMedalTier = (killCount) => {
        const index = killCounts.indexOf(killCount);
        if (index === 0) return 1; // Or
        if (index === 1) return 2; // Argent
        if (index === 2) return 3; // Bronze
        return 0; // Pas de médaille
    };
    
    players.forEach((player, index) => {
        const rank = index + 1;
        const killCount = player.kill_count || 0;
        const medalTier = getMedalTier(killCount);
        
        const entry = document.createElement('div');
        entry.className = 'leaderboard-entry';
        
        // Classe spéciale pour les médailles
        let rankClass = '';
        let rankDisplay = rank;
        
        if (medalTier === 1) {
            rankClass = ' rank-1';
            rankDisplay = '🥇';
        } else if (medalTier === 2) {
            rankClass = ' rank-2';
            rankDisplay = '🥈';
        } else if (medalTier === 3) {
            rankClass = ' rank-3';
            rankDisplay = '🥉';
        }
        
        const photoUrl = getDriveImageUrl(player.person_photo, 500);
        
        entry.innerHTML = `
            <div class="leaderboard-rank${rankClass}">${rankDisplay}</div>
            <div class="leaderboard-photo-container">
                <img src="${photoUrl}" 
                     alt="${player.nickname}"
                     class="leaderboard-photo"
                     loading="lazy">
            </div>
            <div class="leaderboard-info">
                <div>
                    <span class="leaderboard-name">${player.nickname}</span>
                    <span class="leaderboard-year">${player.year}</span>
                </div>
                <div class="leaderboard-kills">${killCount}</div>
            </div>
        `;
        
        leaderboardList.appendChild(entry);
    });
}

// Vérifier si l'utilisateur est connecté au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    // Vérifier si l'utilisateur est connecté
    checkLoggedIn();
    
    [playerPersonPhoto, targetPersonPhoto, newTargetPersonPhoto, modalImage].forEach(img => {
        if (img) {
            img.referrerPolicy = 'no-referrer';
        }
    });

    // Ajouter l'événement de clic sur le logo U56
    const logo = document.querySelector('.logo');
    if (logo) {
        logo.addEventListener('click', playRandomPetSound);
        logo.style.cursor = 'pointer'; // Changer le curseur pour indiquer que c'est cliquable
    }

    // Configurer les boutons de catégorie du trombinoscope
    const categoryButtons = document.querySelectorAll('.trombi-category-btn');
    categoryButtons.forEach(btn => {
        btn.addEventListener('click', (event) => {
            event.preventDefault();
            
            // Ignorer le clic si le bouton est désactivé
            if (btn.disabled || btn.classList.contains('disabled')) {
                return;
            }
            
            const category = btn.dataset.category;
            if (category && category !== currentTrombiCategory) {
                currentTrombiCategory = category;
                
                // Mettre à jour l'état actif des boutons
                categoryButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Mettre à jour la visibilité du texte d'aide pour la catégorie admin
                const adminHint = document.getElementById('admin-category-hint');
                if (adminHint) {
                    if (category === 'admin') {
                        adminHint.classList.add('visible');
                    } else {
                        adminHint.classList.remove('visible');
                    }
                }
                
                // Re-rendre le trombinoscope avec le filtre
                renderTrombi();
            }
        });
    });
    
    // Configurer les événements pour la modale des photos avec vérifications
    if (playerPersonPhoto) {
        playerPersonPhoto.addEventListener('click', () => {
            if (playerPersonPhoto.src) openPhotoModal(playerPersonPhoto.src);
        });
    }
    
    if (targetPersonPhoto) {
        targetPersonPhoto.addEventListener('click', () => {
            if (targetPersonPhoto.src) openPhotoModal(targetPersonPhoto.src);
        });
    }
    
    // Fermer la modale
    if (closeModal) {
        closeModal.addEventListener('click', closePhotoModal);
    }
    
    if (photoModal) {
        photoModal.addEventListener('click', (event) => {
            if (event.target === photoModal) {
                closePhotoModal();
            }
        });
    }

    if (adminRefreshBtn) {
        adminRefreshBtn.addEventListener('click', (event) => {
            event.preventDefault();
            loadAdminOverview();
        });
    }

    // Configurer les boutons de catégorie admin
    const adminCategoryButtons = document.querySelectorAll('.admin-category-btn');
    adminCategoryButtons.forEach(btn => {
        btn.addEventListener('click', (event) => {
            event.preventDefault();
            
            const category = btn.dataset.adminCategory;
            if (category && category !== currentAdminCategory) {
                currentAdminCategory = category;
                
                // Mettre à jour l'état actif des boutons
                adminCategoryButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Re-rendre la vue admin avec le filtre
                applyAdminSortAndRender();
            }
        });
    });

    adminSortHeaders = Array.isArray(adminSortHeaders) ? adminSortHeaders : [];
    adminSortHeaders = Array.from(document.querySelectorAll('.admin-table th.sortable'));
    adminSortHeaders.forEach(header => {
        header.addEventListener('click', (event) => {
            event.preventDefault();
            const sortKey = header.dataset ? header.dataset.sortKey : null;
            handleAdminSort(sortKey);
        });
    });

    updateAdminSortIndicators();
});

// Event Listeners
loginForm.addEventListener('submit', handleLogin);
killedBtn.addEventListener('click', handleKilled);
giveUpBtn.addEventListener('click', handleGiveUp);
logoutBtn.addEventListener('click', handleLogout);
closeNotification.addEventListener('click', closeKillNotification);

/**
 * Vérifie si l'utilisateur est déjà connecté
 */
function checkLoggedIn() {
    fetch('/api/me')
    .then(response => {
        if (response.ok) {
            response.json().then(data => {
                if (data && data.success) {
                    showPlayerInterface(data);
                } else {
                    console.warn('Réponse reçue mais format invalide:', data);
                    showLoginForm();
                    displayError('Erreur du serveur: format de réponse invalide');
                }
            }).catch(error => {
                console.error('Erreur lors du parsing JSON:', error);
                showLoginForm();
                displayError('Erreur du serveur: impossible de lire la réponse');
            });
        } else {
            if (response.status === 401) {
                // Non connecté, rien à faire, le formulaire de connexion est déjà affiché
                showLoginForm();
            } else {
                showLoginForm();
                console.error('Erreur lors de la vérification de la connexion:', response.status);
                displayError(`Erreur du serveur: ${response.status}`);
            }
        }
    })
    .catch(error => {
        console.error('Erreur de connexion au serveur:', error);
        showLoginForm();
        displayError('Impossible de se connecter au serveur. Veuillez réessayer plus tard.');
    });
}

/**
 * Gère la soumission du formulaire de connexion
 */
function handleLogin(e) {
    e.preventDefault();
    
    const nickname = document.getElementById('nickname').value.trim();
    const password = document.getElementById('password').value.trim();
    
    if (!nickname || !password) {
        displayError('Veuillez remplir tous les champs');
        return;
    }
    
    const loginData = {
        nickname: nickname,
        password: password
    };
    
    fetch('/api/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(loginData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showPlayerInterface(data);
        } else {
            displayError(data.message || 'Erreur de connexion');
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        displayError('Erreur de connexion au serveur');
    });
}

/**
 * Cette fonction a été supprimée car le bouton "J'ai tué ma cible" a été retiré.
 * Les administrateurs du jeu sont désormais les seuls à pouvoir valider les kills.
 */

/**
 * Gère la déconnexion
 */
function handleLogout() {
    fetch('/api/logout', {
        method: 'POST'
    })
    .then(() => {
        showLoginForm();
    })
    .catch(error => {
        console.error('Erreur:', error);
        alert('Erreur lors de la déconnexion');
    });
}

/**
 * Affiche le formulaire de connexion
 */
function showLoginForm() {
    stopTrombiUpdates();
    resetTrombiDisplay();
    stopAdminOverviewUpdates();
    resetAdminOverviewDisplay();
    currentPlayerIsAdmin = false;
    if (adminOverviewSection) {
        adminOverviewSection.classList.add('hidden');
    }
    if (podiumSection) {
        podiumSection.classList.add('hidden');
    }
    currentPlayerNickname = null;
    playerContainer.classList.add('hidden');
    loginContainer.classList.remove('hidden');
    loginForm.reset();
    loginError.textContent = '';
}

/**
 * Affiche l'interface du joueur avec ses informations et sa cible
 */
function showPlayerInterface(data) {
    // Vérifier si les données sont valides
    if (!data || !data.player) {
        console.error("Données de joueur invalides", data);
        displayError("Erreur: Impossible de récupérer les données du joueur");
        return;
    }
    
    const normalizedPlayerNickname = typeof data.player.nickname === 'string' ? data.player.nickname.trim() : '';
    currentPlayerNickname = normalizedPlayerNickname || null;
    viewerStatus = (data.player.status || 'alive').toLowerCase();
    currentPlayerIsAdmin = Boolean(data.player.is_admin);
    loginContainer.classList.add('hidden');
    playerContainer.classList.remove('hidden');
    
    // Informations du joueur
    if (playerNicknameHeader) {
        playerNicknameHeader.textContent = normalizedPlayerNickname || "Joueur";
    }
    
    // Gérer l'état du joueur (mort, vivant, abandonné)
    if (data.player.status && data.player.status.toLowerCase() === "dead") {
        // Le joueur est mort, désactiver et cacher les boutons et la section cible
        if (killedBtn) killedBtn.disabled = true;
        if (giveUpBtn) giveUpBtn.disabled = true;
        if (actionButtons) actionButtons.classList.add('hidden');
        if (targetInfoSection) targetInfoSection.classList.add('hidden');
        playerContainer.classList.add('player-dead');
    } else if (data.player.status && data.player.status.toLowerCase() === "gaveup") {
        // Le joueur a abandonné, désactiver et cacher les boutons et la section cible
        if (killedBtn) killedBtn.disabled = true;
        if (giveUpBtn) giveUpBtn.disabled = true;
        if (actionButtons) actionButtons.classList.add('hidden');
        if (targetInfoSection) targetInfoSection.classList.add('hidden');
        playerContainer.classList.add('player-gave-up');
    } else {
        // Le joueur est vivant, activer les boutons et afficher la section cible
        if (killedBtn) killedBtn.disabled = false;
        if (giveUpBtn) giveUpBtn.disabled = false;
        if (actionButtons) actionButtons.classList.remove('hidden');
        if (targetInfoSection) targetInfoSection.classList.remove('hidden');
        playerContainer.classList.remove('player-dead');
        playerContainer.classList.remove('player-gave-up');
    }
    
    // Photos du joueur
    if (playerPersonPhoto && data.player.person_photo) {
        try {
            // Utiliser le format d'intégration d'image Google Drive
            playerPersonPhoto.src = getDriveImageUrl(data.player.person_photo, 500);
            
            // Détecter les erreurs de chargement (permissions Drive manquantes)
            playerPersonPhoto.onerror = () => {
                console.warn("Photo du joueur inaccessible (permissions Google Drive):", data.player.person_photo);
                if (playerPersonPhotoContainer) {
                    playerPersonPhotoContainer.classList.add('photo-error');
                    playerPersonPhotoContainer.title = 'Photo inaccessible - permissions Google Drive manquantes';
                }
            };
            
            if (playerPersonPhotoContainer) playerPersonPhotoContainer.classList.remove('hidden');
        } catch (error) {
            console.error("Erreur lors du chargement de la photo du joueur:", error);
            if (playerPersonPhotoContainer) playerPersonPhotoContainer.classList.add('hidden');
        }
    } else {
        if (playerPersonPhotoContainer) playerPersonPhotoContainer.classList.add('hidden');
    }
    
    if (adminOverviewSection) {
        if (currentPlayerIsAdmin) {
            adminOverviewSection.classList.remove('hidden');
            startAdminOverviewUpdates();
        } else {
            adminOverviewSection.classList.add('hidden');
            stopAdminOverviewUpdates();
            resetAdminOverviewDisplay();
        }
    }

    // Les photos de pieds du joueur principal ne sont plus affichées dans le nouveau design
    // Le code est conservé pour la compatibilité avec les anciennes versions
    try {
        if (playerFeetPhoto && data.player.feet_photo) {
            playerFeetPhoto.src = getDriveImageUrl(data.player.feet_photo, 500);
        }
    } catch (error) {
        console.error("Photo des pieds ignorée:", error);
    }
    
    // Informations de la cible
    if (data.target) {
        try {
            updateTargetInfo(data.target);
            if (targetCard) targetCard.classList.remove('hidden');
            if (noTargetMessage) noTargetMessage.classList.add('hidden');
        } catch (error) {
            console.error("Erreur lors de la mise à jour des informations de la cible:", error);
            if (noTargetMessage) {
                noTargetMessage.textContent = "Erreur lors du chargement des informations de la cible.";
                noTargetMessage.classList.remove('hidden');
            }
            if (targetCard) targetCard.classList.add('hidden');
        }
    } else {
        if (targetCard) targetCard.classList.add('hidden');
        if (noTargetMessage) {
            noTargetMessage.textContent = "Y'a plus rien à faire ! (fyot)";
            noTargetMessage.classList.remove('hidden');
        }
    }

    startTrombiUpdates();
}

/**
 * Met à jour les informations de la cible dans l'interface
 */
function updateTargetInfo(target) {
    // Vérifier si les éléments existent avant de les modifier
    if (!target) {
        console.error("Données de cible invalides");
        return;
    }
    
    if (targetNickname && target.nickname) {
        targetNickname.textContent = target.nickname;
    }
    
    if (targetAction && target.action) {
        targetAction.textContent = target.action;
    }
    
    // Photos de la cible
    if (targetPersonPhoto && target.person_photo) {
        try {
            // Vérifier si l'ID est valide (au moins 10 caractères)
            if (target.person_photo && target.person_photo.length > 10) {
                // Utiliser le format d'intégration d'image Google Drive
                targetPersonPhoto.src = getDriveImageUrl(target.person_photo, 500);
                
                // Détecter les erreurs de chargement (permissions Drive manquantes)
                targetPersonPhoto.onerror = () => {
                    console.warn("Photo de la cible inaccessible (permissions Google Drive):", target.person_photo);
                    if (targetPersonPhotoContainer) {
                        targetPersonPhotoContainer.classList.add('photo-error');
                        targetPersonPhotoContainer.title = 'Photo inaccessible - permissions Google Drive manquantes';
                    }
                };
                
                if (targetPersonPhotoContainer) targetPersonPhotoContainer.classList.remove('hidden');
            } else {
                console.warn("ID de photo invalide:", target.person_photo);
                targetPersonPhoto.src = ""; // Image vide
                if (targetPersonPhotoContainer) targetPersonPhotoContainer.classList.add('hidden');
            }
        } catch (error) {
            console.error("Erreur lors du chargement de la photo de la cible:", error);
            if (targetPersonPhotoContainer) targetPersonPhotoContainer.classList.add('hidden');
        }
    } else {
        if (targetPersonPhotoContainer) targetPersonPhotoContainer.classList.add('hidden');
    }
    
    // Photo des pieds de la cible - affichée via bouton qui ouvre la modale
    if (target.feet_photo && target.feet_photo.length > 10) {
        const feetPhotoUrl = getDriveImageUrl(target.feet_photo, 600);
        updateTargetFeetButton(true, feetPhotoUrl);
    } else {
        updateTargetFeetButton(false, null);
    }
}

/**
 * Met à jour l'état du bouton "voir ses pieds" pour la cible
 */
/**
 * Met à jour l'état du bouton "voir ses pieds" pour la cible
 */
function updateTargetFeetButton(hasPhoto, feetPhotoUrl) {
    const targetCard = document.getElementById('target-card');
    if (!targetCard) return;
    
    let feetButton = document.getElementById('target-feet-toggle-btn');
    
    if (hasPhoto && feetPhotoUrl) {
        // Créer le bouton s'il n'existe pas
        if (!feetButton) {
            feetButton = document.createElement('button');
            feetButton.id = 'target-feet-toggle-btn';
            feetButton.className = 'feet-toggle-btn';
            feetButton.type = 'button';
            feetButton.textContent = 'voir ses pieds';
            
            // Insérer le bouton après la section des photos
            const targetPhotos = targetCard.querySelector('.target-photos');
            if (targetPhotos) {
                targetPhotos.parentNode.insertBefore(feetButton, targetPhotos.nextSibling);
            }
        }
        
        // Mettre à jour l'événement de clic pour ouvrir la modale
        feetButton.onclick = () => {
            openPhotoModal(feetPhotoUrl);
        };
        
        feetButton.classList.remove('hidden');
    } else {
        // Cacher le bouton s'il existe
        if (feetButton) {
            feetButton.classList.add('hidden');
        }
    }
}

/**
 * Affiche un message d'erreur
 */
function displayError(message) {
    loginError.textContent = message;
}

/**
 * Ferme la notification après un kill
 */
function closeKillNotification() {
    killNotification.classList.add('hidden');
}

/**
 * Gère l'action quand un joueur déclare avoir été tué
 */
function handleKilled(e) {
    e.preventDefault();
    
    // Confirmation avant de procéder

    if (!confirm("t'es sûr de vouloir mourir ? après tu pourras plus jouer c'est triste en vrai (gros fyot)")) {
        return;
    }
    
    fetch('/api/killed', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("T'es définitivement éliminé ! aller on retourne capser hophop fyot");
            // Mettre à jour l'interface pour montrer que le joueur est mort
            targetCard.classList.add('hidden');
            noTargetMessage.textContent = "Tu t'es pas géré gros fyot. La str continue sans toi !";
            noTargetMessage.classList.remove('hidden');
            
            // Désactiver et cacher les boutons d'action
            killedBtn.disabled = true;
            giveUpBtn.disabled = true;
            if (actionButtons) actionButtons.classList.add('hidden');
            
            // Cacher la section cible
            if (targetInfoSection) targetInfoSection.classList.add('hidden');
            
            // Ajouter une classe pour indiquer visuellement que le joueur est mort
            playerContainer.classList.add('player-dead');
            viewerStatus = 'dead';
            viewerCanSeeStatus = true;
            loadTrombi();
            loadPodium();
            loadLeaderboard();
        } else {
            alert(`Erreur: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        alert('Erreur de communication avec le serveur');
    });
}

/**
 * Gère l'action quand un joueur abandonne le jeu
 */
function handleGiveUp(e) {
    e.preventDefault();
    
    // Confirmation avant de procéder
    if (!confirm("Êtes-vous sûr de vouloir abandonner le jeu ? Cette action ne peut pas être annulée.")) {
        return;
    }
    
    fetch('/api/giveup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Vous avez abandonné le jeu. Votre cible a été réassignée.");
            // Mettre à jour l'interface pour montrer que le joueur a abandonné
            targetCard.classList.add('hidden');
            noTargetMessage.textContent = "Vous avez abandonné le jeu. Merci d'avoir participé!";
            noTargetMessage.classList.remove('hidden');
            
            // Désactiver et cacher les boutons d'action
            killedBtn.disabled = true;
            giveUpBtn.disabled = true;
            if (actionButtons) actionButtons.classList.add('hidden');
            
            // Cacher la section cible
            if (targetInfoSection) targetInfoSection.classList.add('hidden');
            
            // Ajouter une classe pour indiquer visuellement que le joueur a abandonné
            playerContainer.classList.add('player-gave-up');
            viewerStatus = 'gaveup';
            viewerCanSeeStatus = false;
            loadTrombi();
            loadLeaderboard();
        } else {
            alert(`Erreur: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        alert('Erreur de communication avec le serveur');
    });
}