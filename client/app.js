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
const leaderboardSection = document.getElementById('leaderboard-section');
const leaderboardBody = document.getElementById('leaderboard-body');
const leaderboardEmpty = document.getElementById('leaderboard-empty');
const leaderboardError = document.getElementById('leaderboard-error');
const adminOverviewSection = document.getElementById('admin-overview');
const adminOverviewBody = document.getElementById('admin-overview-body');
const adminOverviewEmpty = document.getElementById('admin-overview-empty');
const adminOverviewError = document.getElementById('admin-overview-error');
const adminRefreshBtn = document.getElementById('admin-refresh');

let leaderboardIntervalId = null;
let currentPlayerNickname = null;
let adminOverviewIntervalId = null;
let currentPlayerIsAdmin = false;
let adminOverviewData = [];
let adminOverviewSort = { column: null, direction: 'asc' };
let adminSortHeaders = [];

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

function startLeaderboardUpdates() {
    loadLeaderboard();
    if (leaderboardIntervalId) {
        clearInterval(leaderboardIntervalId);
    }
    leaderboardIntervalId = setInterval(loadLeaderboard, 30000);
}

function stopLeaderboardUpdates() {
    if (leaderboardIntervalId) {
        clearInterval(leaderboardIntervalId);
        leaderboardIntervalId = null;
    }
}

function resetLeaderboardDisplay() {
    if (leaderboardBody) {
        leaderboardBody.innerHTML = '';
    }
    if (leaderboardEmpty) {
        leaderboardEmpty.classList.add('hidden');
    }
    if (leaderboardError) {
        leaderboardError.classList.add('hidden');
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

function loadLeaderboard() {
    if (!leaderboardBody) {
        return;
    }

    if (leaderboardError) {
        leaderboardError.classList.add('hidden');
    }

    fetch('/api/leaderboard')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data || !data.success || !Array.isArray(data.leaderboard)) {
                throw new Error('Format de réponse invalide');
            }
            renderLeaderboard(data.leaderboard);
        })
        .catch(error => {
            console.error('Erreur lors du chargement du leaderboard:', error);
            if (leaderboardError) {
                leaderboardError.classList.remove('hidden');
            }
            if (leaderboardEmpty) {
                leaderboardEmpty.classList.add('hidden');
            }
        });
}

function renderLeaderboard(entries) {
    if (!leaderboardBody) {
        return;
    }

    leaderboardBody.innerHTML = '';

    if (!entries || entries.length === 0) {
        if (leaderboardEmpty) {
            leaderboardEmpty.classList.remove('hidden');
        }
        return;
    }

    if (leaderboardEmpty) {
        leaderboardEmpty.classList.add('hidden');
    }

    entries.forEach((entry, index) => {
        const row = document.createElement('tr');
        row.classList.add('leaderboard-row');

        const nickname = (entry.nickname || '').trim();
        if (currentPlayerNickname && nickname && nickname.toLowerCase() === currentPlayerNickname.toLowerCase()) {
            row.classList.add('leaderboard-row-self');
        }

        const positionCell = document.createElement('td');
        positionCell.textContent = index + 1;

        const nicknameCell = document.createElement('td');
        nicknameCell.textContent = nickname || '???';

        const killsCell = document.createElement('td');
        const killCount = Number.parseInt(entry.kill_count, 10);
        killsCell.textContent = Number.isNaN(killCount) ? '0' : killCount.toString();

        const statusCell = document.createElement('td');
        const statusSpan = document.createElement('span');
        const rawStatus = typeof entry.status === 'string' ? entry.status.toLowerCase() : 'alive';
        const status = ['alive', 'dead', 'gaveup', 'admin'].includes(rawStatus) ? rawStatus : 'alive';
        statusSpan.classList.add('status-pill', `status-${status}`);
        statusSpan.textContent = getStatusLabel(status);
        statusCell.appendChild(statusSpan);

        if (entry.is_admin) {
            row.classList.add('leaderboard-row-admin');
        }

        row.appendChild(positionCell);
        row.appendChild(nicknameCell);
        row.appendChild(killsCell);
        row.appendChild(statusCell);

        leaderboardBody.appendChild(row);
    });
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

        const nicknameCell = document.createElement('td');
        nicknameCell.textContent = player.nickname || '???';

        const statusCell = document.createElement('td');
        statusCell.textContent = player.status || 'inconnu';

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

function getStatusLabel(status) {
    switch (status) {
        case 'dead':
            return 'Mort';
        case 'gaveup':
            return 'A abandonné';
        case 'admin':
            return 'Admin';
        case 'alive':
        default:
            return 'Vivant';
    }
}

// Vérifier si l'utilisateur est connecté au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    // Vérifier si l'utilisateur est connecté
    checkLoggedIn();
    
    // Ajouter l'événement de clic sur le logo U56
    const logo = document.querySelector('.logo');
    if (logo) {
        logo.addEventListener('click', playRandomPetSound);
        logo.style.cursor = 'pointer'; // Changer le curseur pour indiquer que c'est cliquable
    }
    
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
    stopLeaderboardUpdates();
    resetLeaderboardDisplay();
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
    
    currentPlayerNickname = data.player.nickname || null;
    currentPlayerIsAdmin = Boolean(data.player.is_admin);
    loginContainer.classList.add('hidden');
    playerContainer.classList.remove('hidden');
    
    // Informations du joueur
    if (playerNicknameHeader) {
        playerNicknameHeader.textContent = data.player.nickname || "Joueur";
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
            playerPersonPhoto.src = `https://drive.google.com/thumbnail?id=${data.player.person_photo}&sz=w500`;
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
            playerFeetPhoto.src = `https://drive.google.com/thumbnail?id=${data.player.feet_photo}&sz=w500`;
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

    startLeaderboardUpdates();
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
                targetPersonPhoto.src = `https://drive.google.com/thumbnail?id=${target.person_photo}&sz=w500`;
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
                targetFeetPhoto.src = `https://drive.google.com/thumbnail?id=${target.feet_photo}&sz=w500`;
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
            
            // Désactiver les boutons d'action
            killedBtn.disabled = true;
            giveUpBtn.disabled = true;
            
            // Ajouter une classe pour indiquer visuellement que le joueur a abandonné
            playerContainer.classList.add('player-gave-up');

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