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
const targetFeetPhoto = document.getElementById('target-feet-photo');
const targetPersonPhotoContainer = document.getElementById('target-person-photo-container');
const targetFeetPhotoContainer = document.getElementById('target-feet-photo-container');
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
    if (trombiIntervalId) {
        clearInterval(trombiIntervalId);
    }
    trombiIntervalId = setInterval(loadTrombi, 30000);
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

        if (viewerCanSeeStatus && typeof player.status === 'string' && player.status) {
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

    const metaContainer = document.createElement('div');
    metaContainer.classList.add('trombi-meta');
    let metaHasContent = false;

    if (viewerCanSeeStatus && typeof player.status === 'string' && player.status) {
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

    if (viewerCanSeeStatus && player.status && player.status.toLowerCase() === 'dead') {
        const info = document.createElement('p');
        info.classList.add('trombi-status-info');
        info.textContent = 'Ce joueur a été éliminé.';
        trombiDetails.appendChild(info);
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

    players.forEach(player => {
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
            return 'A abandonné';
        case 'alive':
        default:
            return 'Vivant';
    }
}

// Vérifier si l'utilisateur est connecté au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    // Vérifier si l'utilisateur est connecté
    checkLoggedIn();
    
    [playerPersonPhoto, targetPersonPhoto, targetFeetPhoto, newTargetPersonPhoto, modalImage].forEach(img => {
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
            const category = btn.dataset.category;
            if (category && category !== currentTrombiCategory) {
                currentTrombiCategory = category;
                
                // Mettre à jour l'état actif des boutons
                categoryButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
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
    
    if (targetFeetPhoto) {
        targetFeetPhoto.addEventListener('click', () => {
            if (targetFeetPhoto.src) openPhotoModal(targetFeetPhoto.src);
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
        // Le joueur est mort, désactiver les boutons
        if (killedBtn) killedBtn.disabled = true;
        if (giveUpBtn) giveUpBtn.disabled = true;
        playerContainer.classList.add('player-dead');
    } else if (data.player.status && data.player.status.toLowerCase() === "gaveup") {
        // Le joueur a abandonné, désactiver les boutons
        if (killedBtn) killedBtn.disabled = true;
        if (giveUpBtn) giveUpBtn.disabled = true;
        playerContainer.classList.add('player-gave-up');
    } else {
        // Le joueur est vivant, activer les boutons
        if (killedBtn) killedBtn.disabled = false;
        if (giveUpBtn) giveUpBtn.disabled = false;
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
            noTargetMessage.textContent = "Vous n'avez pas de cible active. Le jeu est peut-être terminé ou vous êtes le dernier survivant !";
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
    
    if (targetFeetPhoto && target.feet_photo) {
        try {
            // Vérifier si l'ID est valide (au moins 10 caractères)
            if (target.feet_photo && target.feet_photo.length > 10) {
                // Utiliser le format d'intégration d'image Google Drive
                targetFeetPhoto.src = getDriveImageUrl(target.feet_photo, 500);
                if (targetFeetPhotoContainer) targetFeetPhotoContainer.classList.remove('hidden');
            } else {
                console.warn("ID de photo de pieds invalide:", target.feet_photo);
                if (targetFeetPhotoContainer) targetFeetPhotoContainer.classList.add('hidden');
            }
        } catch (error) {
            console.error("Erreur lors du chargement de la photo des pieds de la cible:", error);
            if (targetFeetPhotoContainer) targetFeetPhotoContainer.classList.add('hidden');
        }
    } else {
        if (targetFeetPhotoContainer) targetFeetPhotoContainer.classList.add('hidden');
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
    if (!confirm("Êtes-vous sûr de vouloir déclarer que vous avez été tué ? Cette action ne peut pas être annulée.")) {
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
            alert("Vous avez été marqué comme éliminé. Merci d'avoir participé au jeu!");
            // Mettre à jour l'interface pour montrer que le joueur est mort
            targetCard.classList.add('hidden');
            noTargetMessage.textContent = "Vous avez été éliminé. Le jeu continue sans vous!";
            noTargetMessage.classList.remove('hidden');
            
            // Désactiver les boutons d'action
            killedBtn.disabled = true;
            giveUpBtn.disabled = true;
            
            // Ajouter une classe pour indiquer visuellement que le joueur est mort
            playerContainer.classList.add('player-dead');
            viewerStatus = 'dead';
            viewerCanSeeStatus = true;
            loadTrombi();
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
            
            // Désactiver les boutons d'action
            killedBtn.disabled = true;
            giveUpBtn.disabled = true;
            
            // Ajouter une classe pour indiquer visuellement que le joueur a abandonné
            playerContainer.classList.add('player-gave-up');
            viewerStatus = 'gaveup';
            viewerCanSeeStatus = false;
            loadTrombi();
        } else {
            alert(`Erreur: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        alert('Erreur de communication avec le serveur');
    });
}