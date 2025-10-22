// Elements DOM
const loginContainer = document.getElementById('login-container');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const playerContainer = document.getElementById('player-container');
const playerNicknameHeader = document.getElementById('player-nickname-header');
const playerRemainingTargets = document.getElementById('player-remaining-targets');
const playerKillCount = document.getElementById('player-kill-count');
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
const targetSectionTitle = document.getElementById('target-section-title');
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
const deadPlayerInfo = document.getElementById('dead-player-info');
const aliveCountMessage = document.getElementById('alive-count-message');
const podiumSection = document.getElementById('podium-section');
const gameOverMessage = document.getElementById('game-over-message');
const leaderboardSection = document.getElementById('leaderboard-section');
const leaderboardList = document.getElementById('leaderboard-list');
const leaderboardEmpty = document.getElementById('leaderboard-empty');
const leaderboardRemaining = document.getElementById('leaderboard-remaining');

// Fonction helper pour accorder les messages selon le genre
function accord(gender, masculine, feminine) {
    const isFemale = gender && (gender.toUpperCase() === 'F' || gender.toLowerCase() === 'femme');
    return isFemale ? feminine : masculine;
}

// Fonction helper pour obtenir le format ordinal (1er, 2ème, 3ème, etc.)
function getOrdinal(number) {
    if (number === 1) return '1er';
    return `${number}ème`;
}

let trombiIntervalId = null;
let currentPlayerNickname = null;
let currentPlayerGender = null;
let trombiPlayers = [];
let currentTrombiSelection = null;
let viewerCanSeeStatus = false;
let viewerStatus = 'alive';
let currentPlayerIsAdmin = false;
let currentTrombiCategory = 'players';
let currentYearFilter = 'all';
let gameIsOver = false; // Partie terminée quand il reste 1 joueur ou moins

// Sons de pet disponibles
const petSounds = [
    './client/sounds/pet1.mp3',
    './client/sounds/pet2.mp3',
    './client/sounds/pet3.mp3',
    './client/sounds/pet4.mp3',
    './client/sounds/pet5.mp3'
];

// Index pour alterner les sons de manière circulaire
let currentPetSoundIndex = 0;

/**
 * Joue un son de pet en alternant de manière circulaire
 */
function playRandomPetSound() {
    const sound = new Audio(petSounds[currentPetSoundIndex]);
    sound.play();
    // Passer au son suivant de manière circulaire
    currentPetSoundIndex = (currentPetSoundIndex + 1) % petSounds.length;
}

function getDriveImageUrl(fileId, size = 400) {
    if (!fileId || typeof fileId !== 'string') {
        return '';
    }
    const trimmedId = fileId.trim();
    if (!trimmedId) {
        return '';
    }
    const encodedId = encodeURIComponent(trimmedId);
    // Cache plus long : 5 minutes au lieu de 1 minute
    const cacheBuster = Math.floor(Date.now() / 300000);
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
    loadLeaderboard();
    loadTrombi();
    loadPodium();
    if (trombiIntervalId) {
        clearInterval(trombiIntervalId);
    }
    // Augmenter l'intervalle à 45 secondes pour réduire la charge serveur
    trombiIntervalId = setInterval(() => {
        loadLeaderboard();
        loadTrombi();
        loadPodium();
    }, 45000);
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
            updateYearFilterButtons();
            updateDeadPlayerInfo();
            updatePlayerStats();
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

function updatePlayerStats() {
    // Ne plus afficher ces statistiques en haut du profil
    // Elles seront affichées dans le leaderboard à la place
    if (playerRemainingTargets) {
        playerRemainingTargets.classList.add('hidden');
    }
    if (playerKillCount) {
        playerKillCount.classList.add('hidden');
    }
}

function updateYearFilterButtons() {
    const yearFiltersContainer = document.getElementById('trombi-year-filters');
    if (!yearFiltersContainer) return;
    
    // Extraire toutes les années uniques des joueurs (non-admins seulement)
    const years = new Set();
    trombiPlayers.forEach(player => {
        if (!player.is_admin && player.year) {
            years.add(player.year);
        }
    });
    
    // Trier les années (0A, 2A, 3A, 4A, 5A, etc.)
    const sortedYears = Array.from(years).sort((a, b) => {
        const numA = parseInt(a);
        const numB = parseInt(b);
        return numA - numB;
    });
    
    // Générer les boutons
    yearFiltersContainer.innerHTML = '';
    
    // Bouton "Tous"
    const allBtn = document.createElement('button');
    allBtn.type = 'button';
    allBtn.className = 'trombi-year-btn active';
    allBtn.dataset.year = 'all';
    allBtn.textContent = 'Tous';
    yearFiltersContainer.appendChild(allBtn);
    
    // Boutons pour chaque année
    sortedYears.forEach(year => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'trombi-year-btn';
        btn.dataset.year = year;
        btn.textContent = year;
        yearFiltersContainer.appendChild(btn);
    });
    
    // Ajouter les événements de clic
    const yearButtons = yearFiltersContainer.querySelectorAll('.trombi-year-btn');
    yearButtons.forEach(btn => {
        btn.addEventListener('click', (event) => {
            event.preventDefault();
            
            const year = btn.dataset.year;
            if (year && year !== currentYearFilter) {
                currentYearFilter = year;
                
                // Réinitialiser la sélection
                currentTrombiSelection = null;
                
                // Vider les détails du trombinoscope
                if (trombiDetails) {
                    trombiDetails.innerHTML = '<p class="trombi-placeholder">Sélectionne un joueur pour découvrir son profil.</p>';
                }
                
                // Mettre à jour l'état actif des boutons
                yearButtons.forEach(yb => yb.classList.remove('active'));
                btn.classList.add('active');
                
                // Re-rendre le trombinoscope avec le filtre
                renderTrombi();
            }
        });
    });
    
    // Afficher les filtres d'année si la catégorie active est "players"
    if (currentTrombiCategory === 'players') {
        yearFiltersContainer.classList.remove('hidden');
    } else {
        yearFiltersContainer.classList.add('hidden');
    }
}

function updateTrombiCategoryButtons() {
    const categoryButtons = document.querySelectorAll('.trombi-category-btn');
    
    categoryButtons.forEach(btn => {
        const category = btn.dataset.category;
        const isAdminOnly = btn.classList.contains('admin-only');
        const isNonAdminOnly = btn.classList.contains('non-admin-only');
        
        if (currentPlayerIsAdmin) {
            // Pour les admins : afficher les catégories admin, cacher les catégories non-admin
            if (isAdminOnly) {
                btn.classList.remove('hidden');
            } else if (isNonAdminOnly) {
                btn.classList.add('hidden');
            }
        } else {
            // Pour les non-admins : afficher les catégories non-admin, cacher les catégories admin
            if (isNonAdminOnly) {
                btn.classList.remove('hidden');
            } else if (isAdminOnly) {
                btn.classList.add('hidden');
            }
        }
        
        // Activer le bouton correspondant à la catégorie actuelle
        if (category === currentTrombiCategory) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

function updateDeadPlayerInfo() {
    // Cette fonction n'est plus utilisée - le message est affiché dans le leaderboard
    if (deadPlayerInfo) {
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
        return;
    }

    if (trombiEmpty) {
        trombiEmpty.classList.add('hidden');
    }

    // Filtrer selon la catégorie sélectionnée
    const filteredPlayers = trombiPlayers.filter(player => {
        let categoryMatch = false;
        
        if (currentTrombiCategory === 'all') {
            categoryMatch = true;
        } else if (currentTrombiCategory === 'alive') {
            const status = (player.status || 'alive').toLowerCase();
            // Exclure les admins de la catégorie "vivants"
            categoryMatch = status === 'alive' && !player.is_admin;
        } else if (currentTrombiCategory === 'dead') {
            const status = (player.status || 'alive').toLowerCase();
            // Pour la catégorie "Morts", ne plus inclure les abandons
            categoryMatch = status === 'dead';
        } else if (currentTrombiCategory === 'gaveup') {
            const status = (player.status || 'alive').toLowerCase();
            // Catégorie "Abandons" - uniquement pour les admins
            categoryMatch = status === 'gaveup';
        } else if (currentTrombiCategory === 'players') {
            // Catégorie "Joueurs" pour les non-admins : tous les joueurs SAUF les admins
            categoryMatch = !player.is_admin;
        } else if (currentTrombiCategory === 'admins') {
            // Catégorie "Admins" pour les non-admins : seulement les admins
            categoryMatch = player.is_admin;
        } else {
            categoryMatch = true;
        }
        
        // Si on est dans la catégorie "Joueurs", appliquer le filtre d'année
        if (categoryMatch && currentTrombiCategory === 'players' && currentYearFilter !== 'all') {
            const yearMatch = player.year === currentYearFilter;
            return yearMatch;
        }
        
        return categoryMatch;
    });

    if (filteredPlayers.length === 0) {
        if (trombiEmpty) {
            trombiEmpty.classList.remove('hidden');
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

        // Affichage du statut pour les admins (à côté de l'année)
        // Les admins (joueurs avec is_admin=true) n'ont PAS de badge de statut car ils ne participent pas au jeu
        if ((currentPlayerIsAdmin || gameIsOver) && !player.is_admin) {
            const normalizedStatus = typeof player.status === 'string' ? player.status.toLowerCase() : 'alive';
            
            // Pour les admins : si le joueur est vivant, afficher sa cible au lieu du badge "Vivant"
            if (currentPlayerIsAdmin && normalizedStatus === 'alive' && player.target) {
                const targetChip = document.createElement('span');
                targetChip.classList.add('status-pill', 'status-target');
                targetChip.textContent = `→ ${player.target}`;
                targetChip.style.cursor = 'pointer';
                targetChip.title = `Cible: ${player.target}`;
                targetChip.addEventListener('click', (e) => {
                    e.stopPropagation();
                    selectTrombiEntry(player.target);
                });
                labelWrapper.appendChild(targetChip);
            } else {
                // Pour les autres cas (mort, abandonné) ou si partie terminée : afficher le statut normal
                const statusChip = document.createElement('span');
                
                if (typeof player.status === 'string' && player.status) {
                    statusChip.classList.add('status-pill', `status-${normalizedStatus}`);
                    statusChip.textContent = getStatusLabel(normalizedStatus);
                }
                
                if (statusChip.textContent) {
                    labelWrapper.appendChild(statusChip);
                }
            }
        }

        if (player.is_admin) {
            const adminBadge = createAdminBadge();
            labelWrapper.appendChild(adminBadge);
        }

        entryButton.appendChild(labelWrapper);

        // Afficher le nombre de kills à droite pour les admins ou quand la partie est terminée
        if ((currentPlayerIsAdmin || gameIsOver) && !player.is_admin) {
            const killCount = player.kill_count || 0;
            const killBadge = document.createElement('span');
            killBadge.classList.add('trombi-kill-badge');
            killBadge.textContent = `${killCount} 🗡️`;
            killBadge.setAttribute('aria-label', `${killCount} kill${killCount > 1 ? 's' : ''}`);
            entryButton.appendChild(killBadge);
        }

        if (currentPlayerNickname && nickname && nickname.toLowerCase() === currentPlayerNickname.toLowerCase()) {
            entryButton.classList.add('trombi-entry-self');
        }

        if (currentSelectionName && nickname.toLowerCase() === currentSelectionName) {
            entryButton.classList.add('selected');
        }

        entryButton.addEventListener('click', () => {
            selectTrombiEntry(nickname);
        });

        trombiList.appendChild(entryButton);
    });

    // Ne plus sélectionner automatiquement le premier joueur
    // Sélectionner uniquement si un joueur était déjà sélectionné et est toujours dans la liste filtrée
    if (currentTrombiSelection) {
        const isCurrentInFiltered = filteredPlayers.some(p => 
            (p.nickname || '').trim().toLowerCase() === currentTrombiSelection.toLowerCase()
        );
        if (isCurrentInFiltered) {
            selectTrombiEntry(currentTrombiSelection);
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

    // Affichage du badge de statut pour les admins (sur la même ligne que le nom)
    // Les admins (joueurs avec is_admin=true) n'ont PAS de badge de statut car ils ne participent pas au jeu
    if ((currentPlayerIsAdmin || gameIsOver) && !player.is_admin) {
        const statusPill = document.createElement('span');
        
        // Afficher le statut uniquement pour les non-admins
        if (typeof player.status === 'string' && player.status) {
            const normalizedStatus = player.status.toLowerCase();
            statusPill.classList.add('status-pill', `status-${normalizedStatus}`);
            statusPill.textContent = getStatusLabel(normalizedStatus);
            statusPill.setAttribute('aria-label', `Statut: ${getStatusLabel(normalizedStatus)}`);
        }
        
        if (statusPill.textContent) {
            title.appendChild(statusPill);
        }
    }

    if (player.is_admin) {
        const adminBadge = createAdminBadge();
        title.appendChild(adminBadge);
    }

    trombiDetails.appendChild(title);

    // === POUR LES ADMINS OU QUAND LA PARTIE EST TERMINÉE ===
    if ((currentPlayerIsAdmin || gameIsOver) && !player.is_admin) {
        const isDead = player.status && (player.status.toLowerCase() === 'dead' || player.status.toLowerCase() === 'gaveup');
        const isAlive = !isDead;
        
        // === JOUEUR VIVANT (GAGNANT) ===
        if (isAlive) {
            // Si c'est le gagnant (partie terminée et vivant), afficher un message spécial
            if (gameIsOver) {
                // Afficher la boîte GAGNANT uniquement si :
                // - Il y a exactement UN joueur non-admin avec un statut explicite 'alive'
                // - Le joueur inspecté est ce joueur non-admin vivant
                // Protection supplémentaire : vérifier que le statut du joueur inspecté est explicitement 'alive'
                const aliveNonAdmin = trombiPlayers.filter(p => typeof p.status === 'string' && p.status.toLowerCase() === 'alive' && !p.is_admin);
                const sole = aliveNonAdmin.length === 1 ? aliveNonAdmin[0] : null;
                const isSoleWinner = sole && sole.nickname && player.nickname && sole.nickname.toLowerCase() === player.nickname.toLowerCase() && !player.is_admin && typeof player.status === 'string' && player.status.toLowerCase() === 'alive';
                if (isSoleWinner) {
                    const winnerInfoP = document.createElement('div');
                    winnerInfoP.classList.add('trombi-winner-box');

                    const winnerText = document.createElement('div');
                    winnerText.textContent = '🏆 GAGNANT 🏆';
                    winnerText.classList.add('winner-title');
                    winnerInfoP.appendChild(winnerText);

                    // Chercher le dernier joueur tué par le gagnant
                    // = celui avec killed_by = gagnant et le plus grand elimination_order
                    const playersKilledByWinner = trombiPlayers.filter(p => 
                        p.killed_by && typeof p.killed_by === 'string' && p.killed_by.toLowerCase() === player.nickname.toLowerCase()
                    );

                    if (playersKilledByWinner.length > 0) {
                        // Trier par elimination_order décroissant et prendre le premier
                        playersKilledByWinner.sort((a, b) => {
                            const orderA = parseInt(a.elimination_order, 10) || 0;
                            const orderB = parseInt(b.elimination_order, 10) || 0;
                            return orderB - orderA;
                        });

                        const lastKilled = playersKilledByWinner[0];

                        const lastKillDiv = document.createElement('div');
                        lastKillDiv.classList.add('winner-last-kill');

                        lastKillDiv.appendChild(document.createTextNode('Son dernier kill était '));

                        const killedLink = document.createElement('span');
                        killedLink.classList.add('trombi-target-link');
                        killedLink.textContent = lastKilled.nickname;
                        killedLink.addEventListener('click', (e) => {
                            e.stopPropagation();
                            selectTrombiEntry(lastKilled.nickname);
                        });
                        lastKillDiv.appendChild(killedLink);

                        // Chercher l'action que le gagnant devait faire
                        let actionToDisplay = null;

                        if (player.action && player.target && player.target.toLowerCase() === lastKilled.nickname.toLowerCase()) {
                            actionToDisplay = player.action;
                        } else if (lastKilled.hunter_action) {
                            actionToDisplay = lastKilled.hunter_action;
                        }

                        if (actionToDisplay) {
                            lastKillDiv.appendChild(document.createTextNode(' et '));
                            lastKillDiv.appendChild(document.createTextNode(accord(player.gender, 'il', 'elle')));
                            lastKillDiv.appendChild(document.createTextNode(' devait '));
                            const actionSpan = document.createElement('span');
                            actionSpan.classList.add('action-text');
                            actionSpan.textContent = `"${actionToDisplay}"`;
                            lastKillDiv.appendChild(actionSpan);
                        }

                        winnerInfoP.appendChild(lastKillDiv);
                    }

                    trombiDetails.appendChild(winnerInfoP);
                }
            }
            else {
                // Partie en cours : afficher les infos normales
                // 1. "Chassé par [hunter]" + action du hunter
                if (player.hunter) {
                    const hunterInfoP = document.createElement('div');
                    hunterInfoP.classList.add('trombi-hunter-box');
                    
                    hunterInfoP.appendChild(document.createTextNode('Chassé par '));
                    
                    const hunterLink = document.createElement('span');
                    hunterLink.classList.add('trombi-target-link');
                    hunterLink.textContent = player.hunter;
                    hunterLink.style.cursor = 'pointer';
                    hunterLink.style.textDecoration = 'underline';
                    hunterLink.style.color = 'var(--primary-color)';
                    hunterLink.addEventListener('click', (e) => {
                        e.stopPropagation();
                        selectTrombiEntry(player.hunter);
                    });
                    hunterInfoP.appendChild(hunterLink);
                    
                    if (player.hunter_action) {
                        hunterInfoP.appendChild(document.createElement('br'));
                        const hunterActionSpan = document.createElement('span');
                        hunterActionSpan.style.fontStyle = 'italic';
                        hunterActionSpan.style.fontSize = '0.85rem';
                        hunterActionSpan.style.color = '#888888';
                        hunterActionSpan.textContent = `"${player.hunter_action}"`;
                        hunterInfoP.appendChild(hunterActionSpan);
                    }
                    
                    trombiDetails.appendChild(hunterInfoP);
                }
                
                // 2. "Sa cible est [cible]" + action
                if (player.target) {
                    const targetInfoP = document.createElement('div');
                    targetInfoP.classList.add('trombi-target-box');
                    
                    targetInfoP.appendChild(document.createTextNode('Sa cible est '));
                    
                    const targetLink = document.createElement('span');
                    targetLink.classList.add('trombi-target-link');
                    targetLink.textContent = player.target;
                    targetLink.style.cursor = 'pointer';
                    targetLink.style.textDecoration = 'underline';
                    targetLink.style.color = 'var(--primary-color)';
                    targetLink.addEventListener('click', (e) => {
                        e.stopPropagation();
                        selectTrombiEntry(player.target);
                    });
                    targetInfoP.appendChild(targetLink);
                    
                    if (player.action) {
                        targetInfoP.appendChild(document.createElement('br'));
                        const actionSpan = document.createElement('span');
                        actionSpan.style.fontStyle = 'italic';
                        actionSpan.style.fontSize = '0.85rem';
                        actionSpan.style.color = '#888888';
                        actionSpan.textContent = `"${player.action}"`;
                        targetInfoP.appendChild(actionSpan);
                    }
                    
                    trombiDetails.appendChild(targetInfoP);
                }
            }
        }
        
        // === JOUEUR MORT ===
        if (isDead) {
            // 1. "s'est fait kill par [killer]"
            if (player.killed_by) {
                const killedByInfoP = document.createElement('div');
                killedByInfoP.classList.add('trombi-hunter-box', 'kill-info-box');
                
                const killIcon = document.createElement('span');
                killIcon.classList.add('kill-icon');
                killIcon.textContent = '💀';
                killedByInfoP.appendChild(killIcon);
                
                const killText = document.createElement('span');
                killText.appendChild(document.createTextNode('S\'est fait kill par '));
                
                const killerLink = document.createElement('span');
                killerLink.classList.add('trombi-target-link');
                killerLink.textContent = player.killed_by;
                killerLink.addEventListener('click', (e) => {
                    e.stopPropagation();
                    selectTrombiEntry(player.killed_by);
                });
                killText.appendChild(killerLink);
                killedByInfoP.appendChild(killText);
                
                trombiDetails.appendChild(killedByInfoP);
            }
            
            // 2. "devait kill [cible]" + action
            if (player.target) {
                const targetInfoP = document.createElement('div');
                targetInfoP.classList.add('trombi-target-box', 'kill-info-box');
                
                const targetIcon = document.createElement('span');
                targetIcon.classList.add('kill-icon');
                targetIcon.textContent = '🎯';
                targetInfoP.appendChild(targetIcon);
                
                const targetText = document.createElement('span');
                targetText.appendChild(document.createTextNode('Devait kill '));
                
                const targetLink = document.createElement('span');
                targetLink.classList.add('trombi-target-link');
                targetLink.textContent = player.target;
                targetLink.addEventListener('click', (e) => {
                    e.stopPropagation();
                    selectTrombiEntry(player.target);
                });
                targetText.appendChild(targetLink);
                targetInfoP.appendChild(targetText);
                
                if (player.action) {
                    const actionDiv = document.createElement('div');
                    actionDiv.classList.add('action-text');
                    actionDiv.textContent = `"${player.action}"`;
                    targetInfoP.appendChild(actionDiv);
                }
                
                trombiDetails.appendChild(targetInfoP);
            }
        }
    }

    // Afficher le message info après la cible selon le type de joueur
    if (player.is_admin) {
        // Message d'information pour les admins uniquement
        const adminInfo = document.createElement('p');
        adminInfo.classList.add('trombi-admin-info');
        adminInfo.textContent = 'à contacter en cas de non gérance (au killer)';
        trombiDetails.appendChild(adminInfo);
        
        // Numéro de téléphone pour les admins
        if (player.phone) {
            const phoneContainer = document.createElement('p');
            phoneContainer.classList.add('trombi-phone');
            
            const phoneLink = document.createElement('a');
            phoneLink.href = `tel:${player.phone}`;
            phoneLink.textContent = `📞 ${player.phone}`;
            phoneLink.title = 'Appeler ce numéro';
            
            phoneContainer.appendChild(phoneLink);
            trombiDetails.appendChild(phoneContainer);
        }
    } else {
        // Message des quarts/sénile pour les non-admins uniquement
        let message = '';
        
        // Message basé sur les quarts dans une krô (en premier)
        const kroAnswer = (player.kro_answer || '').trim();
        if (kroAnswer) {
            // Extraire le nombre pour gérer le pluriel correctement
            const numberMatch = kroAnswer.match(/\d+/);
            const hasMultipleQuarts = numberMatch && parseInt(numberMatch[0]) > 1;
            const quartWord = hasMultipleQuarts ? 'quarts' : 'quart';
            
            // Si la réponse contient "Réponse B", ajouter "(gros fyot)"
            if (kroAnswer.toLowerCase().includes('réponse b') || kroAnswer.toLowerCase().includes('reponse b')) {
                message = `${accord(player.gender, 'Ce (gros) fyot pense', 'Cette (grosse) fyotte pense')} qu'il y a ${kroAnswer} ${quartWord} dans une krô`;
            } else {
                message = `${accord(player.gender, 'Ce fyot pense', 'Cette fyotte pense')} qu'il y a ${kroAnswer} ${quartWord} dans une krô`;
            }
        }
        
        // Ajouter la réponse sur "Est-ce que c'était mieux avant ?"
        const beforeAnswer = (player.before_answer || '').trim();
        if (beforeAnswer.toLowerCase().includes('sénile') || beforeAnswer.toLowerCase().includes('senile')) {
            if (message) {
                message += ` et ${accord(player.gender, 'il', 'elle')} est sénile`;
            } else {
                message = `${accord(player.gender, 'Ce joueur', 'Cette joueuse')} est sénile`;
            }
        } else if (beforeAnswer.toLowerCase() === 'non' || beforeAnswer.toLowerCase() === 'no') {
            if (message) {
                message += ' et que c\'était pas mieux avant';
            } else {
                message = `${accord(player.gender, 'Ce fyot pense', 'Cette fyotte pense')} que c'était pas mieux avant`;
            }
        }
        
        if (message) {
            const playerInfo = document.createElement('p');
            playerInfo.classList.add('trombi-admin-info'); // Réutiliser le même style
            playerInfo.textContent = message;
            trombiDetails.appendChild(playerInfo);
        }
    }

    const metaContainer = document.createElement('div');
    metaContainer.classList.add('trombi-meta');
    let metaHasContent = false;

    // Afficher les statistiques pour les admins
    if (currentPlayerIsAdmin) {
        const statsContainer = document.createElement('div');
        statsContainer.classList.add('trombi-admin-stats');
        
        // Ne pas afficher les statistiques de kill pour les admins (ils ne participent pas au jeu)
        if (!player.is_admin) {
            const killCount = player.kill_count || 0;
            
            // Calculer le classement du joueur (exclure les admins du classement)
            if (killCount > 0 && trombiPlayers.length > 0) {
                // Trier les joueurs par kill_count décroissant (sans les admins)
                const sortedPlayers = [...trombiPlayers]
                    .filter(p => !p.is_admin)
                    .sort((a, b) => {
                        const aKills = a.kill_count || 0;
                        const bKills = b.kill_count || 0;
                        return bKills - aKills;
                    });
                
                // Trouver le rang du joueur
                let rank = 1;
                for (let i = 0; i < sortedPlayers.length; i++) {
                    if (sortedPlayers[i].nickname === player.nickname) {
                        rank = i + 1;
                        break;
                    }
                }
                
                const rankText = document.createElement('p');
                rankText.classList.add('trombi-stat-item');
                rankText.innerHTML = `<strong>Classement tueur :</strong> ${rank}/${sortedPlayers.length}`;
                statsContainer.appendChild(rankText);
            }
            
            // Ordre d'élimination si le joueur est mort
            if (player.status && (player.status.toLowerCase() === 'dead' || player.status.toLowerCase() === 'gaveup')) {
                const eliminationOrder = parseInt(player.elimination_order, 10) || 0;
                
                // N = nombre total de joueurs de la partie (ceux avec elimination_order !== -1 ET qui ne sont pas admins)
                const totalActivePlayers = trombiPlayers.filter(p => {
                    const order = p.elimination_order;
                    return !p.is_admin && order !== undefined && order !== null && order !== -1 && order !== "-1";
                }).length;
                
                const orderText = document.createElement('p');
                orderText.classList.add('trombi-stat-item');
                // Format : "Mort en 1er (1/15)" ou "Mort en 5ème (5/15)"
                orderText.innerHTML = `<strong>Mort en ${getOrdinal(eliminationOrder)}</strong> (${eliminationOrder}/${totalActivePlayers})`;
                statsContainer.appendChild(orderText);
            }
        }
        
        // N'ajouter le statsContainer que s'il contient des éléments
        if (statsContainer.children.length > 0) {
            metaContainer.appendChild(statsContainer);
            metaHasContent = true;
        }
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
        placeholder.textContent = `Pas de photo disponible pour ${accord(player.gender, 'ce gros fyot', 'cette grosse fyotte')}.`;
        photoContainer.appendChild(placeholder);
    }

    trombiDetails.appendChild(photoContainer);
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
                gameIsOver = true;
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
                // Forcer le rechargement du trombinoscope pour afficher les infos admin
                loadTrombi();
            } else {
                gameIsOver = false;
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
        
        // Compter les joueurs vivants : ceux avec status === 'alive' ET qui ne sont pas admins
        const aliveCount = (data.leaderboard || []).filter(player => {
            return player.status === 'alive' && !player.is_admin;
        }).length;
        
        // Calculer le nombre total de joueurs actifs (sans admins)
        const totalActivePlayers = (data.leaderboard || []).filter(player => !player.is_admin).length;
        
        // Mettre à jour l'état global de fin de partie
        gameIsOver = aliveCount <= 1;
        
        // Afficher "Il ne reste plus que x/N joueurs en vie" pour tout le monde
        if (leaderboardRemaining) {
            const remainingText = `(Il ne reste plus que ${aliveCount} joueur${aliveCount > 1 ? 's' : ''} en vie sur ${totalActivePlayers})`;
            leaderboardRemaining.textContent = remainingText;
            leaderboardRemaining.classList.remove('hidden');
        }
        
        // Filtrer les joueurs avec au moins 1 kill (exclure les admins)
        const playersWithKills = (data.leaderboard || []).filter(player => (player.kill_count || 0) > 0 && !player.is_admin);
        
        // Trouver le joueur actuel
        const currentPlayer = (data.leaderboard || []).find(p => 
            p.nickname && currentPlayerNickname && 
            p.nickname.toLowerCase() === currentPlayerNickname.toLowerCase()
        );
        
        let playersToDisplay = [];
        
        // Si l'utilisateur est admin OU si la partie est terminée, afficher le top 10
        if (currentPlayerIsAdmin || gameIsOver) {
            playersToDisplay = playersWithKills.slice(0, 10);
            
            // Ajouter l'admin actuel s'il a des kills et n'est pas dans le top 10
            if (currentPlayer && currentPlayer.is_admin && (currentPlayer.kill_count || 0) > 0) {
                const isInTop10 = playersToDisplay.some(p => 
                    p.nickname && p.nickname.toLowerCase() === currentPlayerNickname.toLowerCase()
                );
                
                if (!isInTop10) {
                    playersToDisplay.push(currentPlayer);
                }
            }
        } else {
            // Si l'utilisateur n'est pas admin et que la partie est en cours, afficher uniquement son propre profil
            if (currentPlayer && !currentPlayer.is_admin) {
                // Calculer le classement du joueur parmi tous les joueurs avec kills
                const playerRank = playersWithKills.findIndex(p => 
                    p.nickname && p.nickname.toLowerCase() === currentPlayerNickname.toLowerCase()
                ) + 1;
                
                // Ajouter le rang et le total au joueur
                currentPlayer.displayRank = playerRank > 0 ? playerRank : playersWithKills.length + 1;
                currentPlayer.totalPlayers = totalActivePlayers;
                playersToDisplay = [currentPlayer];
            }
        }
        
        if (playersToDisplay.length === 0) {
            // Afficher le message "Soit le premier à faire un kill !"
            if (leaderboardList) leaderboardList.classList.add('hidden');
            if (leaderboardEmpty) leaderboardEmpty.classList.remove('hidden');
        } else {
            // Afficher le leaderboard
            if (leaderboardEmpty) leaderboardEmpty.classList.add('hidden');
            if (leaderboardList) leaderboardList.classList.remove('hidden');
            renderLeaderboard(playersToDisplay, gameIsOver);
        }
    } catch (error) {
        console.error('Erreur lors du chargement du leaderboard:', error);
    }
}

// Afficher le leaderboard
function renderLeaderboard(players, gameIsOver = false) {
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
        // Utiliser le rang précalculé si disponible (pour les non-admins), sinon utiliser l'index
        const rank = player.displayRank || (index + 1);
        const totalPlayers = player.totalPlayers;
        const killCount = player.kill_count || 0;
        const medalTier = getMedalTier(killCount);
        
        const entry = document.createElement('div');
        entry.className = 'leaderboard-entry';
        
        // Vérifier si c'est le joueur actuel
        const isCurrentPlayer = player.nickname && currentPlayerNickname && 
            player.nickname.toLowerCase() === currentPlayerNickname.toLowerCase();
        
        if (isCurrentPlayer) {
            entry.classList.add('leaderboard-entry-current');
        }
        
        // Classe spéciale pour les médailles (seulement pour les 3 premiers rangs réels)
        let rankClass = '';
        let rankDisplay;
        
        // Si la partie est terminée OU si c'est un admin, afficher les médailles
        // Sinon, si totalPlayers est défini, afficher juste "x" (pour les non-admins en cours de partie)
        if (gameIsOver || !totalPlayers) {
            // Afficher les médailles ou le rang normal
            rankDisplay = rank;
            if (rank === 1 && medalTier === 1) {
                rankClass = ' rank-1';
                rankDisplay = '🥇';
            } else if (rank === 2 && medalTier === 2) {
                rankClass = ' rank-2';
                rankDisplay = '🥈';
            } else if (rank === 3 && medalTier === 3) {
                rankClass = ' rank-3';
                rankDisplay = '🥉';
            }
        } else {
            // Partie en cours, non-admin : afficher juste "x"
            rankDisplay = rank;
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
                
                // Réinitialiser la sélection et le filtre d'année
                currentTrombiSelection = null;
                currentYearFilter = 'all';
                
                // Afficher/masquer les filtres d'année selon la catégorie
                const yearFilters = document.getElementById('trombi-year-filters');
                if (yearFilters) {
                    if (category === 'players') {
                        yearFilters.classList.remove('hidden');
                        // Réinitialiser le bouton actif
                        const yearButtons = yearFilters.querySelectorAll('.trombi-year-btn');
                        yearButtons.forEach(yb => yb.classList.remove('active'));
                        const allYearBtn = yearFilters.querySelector('[data-year="all"]');
                        if (allYearBtn) allYearBtn.classList.add('active');
                    } else {
                        yearFilters.classList.add('hidden');
                    }
                }
                
                // Vider les détails du trombinoscope et afficher le message placeholder
                if (trombiDetails) {
                    trombiDetails.innerHTML = '<p class="trombi-placeholder">Choisis un fyot pour voir sa tête (et ses pieds).</p>';
                }
                
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
    currentPlayerIsAdmin = false;
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
    currentPlayerGender = data.player.gender || null;
    viewerStatus = (data.player.status || 'alive').toLowerCase();
    currentPlayerIsAdmin = Boolean(data.player.is_admin);
    
    // Définir la catégorie par défaut selon si l'utilisateur est admin ou non
    currentTrombiCategory = 'players';
    
    loginContainer.classList.add('hidden');
    playerContainer.classList.remove('hidden');
    
    // Accorder les textes selon le genre du joueur
    if (killedBtn) {
        killedBtn.textContent = `Je suis ${accord(currentPlayerGender, 'mort (gros fyot)', 'morte (grosse fyote)')}`;
    }
    
    // Mettre à jour le message du leaderboard vide
    if (leaderboardEmpty) {
        const leaderboardEmptyP = leaderboardEmpty.querySelector('p');
        if (leaderboardEmptyP) {
            leaderboardEmptyP.textContent = `${accord(currentPlayerGender, 'Soit le premier', 'Sois la première')} à tuer un(e) fyot(te) ! (dans le jeu hein pas en vrai...)`;
        }
    }
    
    // Informations du joueur
    if (playerNicknameHeader) {
        playerNicknameHeader.textContent = normalizedPlayerNickname || "Joueur";
    }
    
    // Afficher les statistiques
    // Pour l'instant, on masque ces éléments et on les mettra à jour après le chargement du trombi
    if (playerRemainingTargets) {
        playerRemainingTargets.classList.add('hidden');
    }
    if (playerKillCount) {
        playerKillCount.classList.add('hidden');
    }
    
    // Gérer l'état du joueur (mort, vivant, abandonné, admin)
    if (currentPlayerIsAdmin) {
        // Les admins n'ont pas accès aux boutons d'action
        if (actionButtons) actionButtons.classList.add('hidden');
        if (killedBtn) killedBtn.classList.add('hidden');
        if (giveUpBtn) giveUpBtn.classList.add('hidden');
        if (targetInfoSection) targetInfoSection.classList.remove('hidden');
        // Ajouter une classe pour styler le bouton de déconnexion en rouge
        playerContainer.classList.add('player-admin');
    } else if (data.player.status && data.player.status.toLowerCase() === "dead") {
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
        if (killedBtn) {
            killedBtn.disabled = false;
            killedBtn.classList.remove('hidden');
        }
        if (giveUpBtn) {
            giveUpBtn.disabled = false;
            giveUpBtn.classList.remove('hidden');
        }
        if (actionButtons) actionButtons.classList.remove('hidden');
        if (targetInfoSection) targetInfoSection.classList.remove('hidden');
        playerContainer.classList.remove('player-dead');
        playerContainer.classList.remove('player-gave-up');
        playerContainer.classList.remove('player-admin');
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
            // Message différent selon si c'est un admin, un joueur mort, ou un joueur sans cible
            if (currentPlayerIsAdmin) {
                noTargetMessage.textContent = "Tu n'as pas de cible, car l'admin ne s'associe pas avec le cafard.";
                // Masquer le titre "TA CIBLE" pour les admins
                if (targetSectionTitle) {
                    targetSectionTitle.classList.add('hidden');
                }
            } else if (viewerStatus === 'dead' || viewerStatus === 'gaveup') {
                // Message pour les joueurs morts ou qui ont abandonné
                noTargetMessage.textContent = `Tu t'es pas ${accord(currentPlayerGender, 'géré gros fyot', 'gérée grosse fyote')}. La str continue sans toi !`;
                // Afficher le titre pour les joueurs morts
                if (targetSectionTitle) {
                    targetSectionTitle.classList.remove('hidden');
                }
            } else {
                noTargetMessage.textContent = `Y'a plus rien à faire ! (${accord(currentPlayerGender, 'fyot', 'fyote')})`;
                // Afficher le titre pour les non-admins
                if (targetSectionTitle) {
                    targetSectionTitle.classList.remove('hidden');
                }
            }
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

    if (!confirm(`t'es ${accord(currentPlayerGender, 'sûr', 'sûre')} de vouloir mourir ? après tu pourras plus jouer c'est triste en vrai (${accord(currentPlayerGender, 'gros fyot', 'grosse fyotte')})`)) {
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
            alert(`T'es définitivement ${accord(currentPlayerGender, 'éliminé', 'éliminée')} ! aller on retourne capser hophop ${accord(currentPlayerGender, 'fyot', 'fyote')}`);
            // Mettre à jour l'interface pour montrer que le joueur est mort
            targetCard.classList.add('hidden');
            noTargetMessage.textContent = `Tu t'es pas ${accord(currentPlayerGender, 'géré gros fyot', 'gérée grosse fyote')}. La str continue sans toi !`;
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
            loadLeaderboard();
            loadTrombi();
            loadPodium();
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
    if (!confirm(`T'es ${accord(currentPlayerGender, 'sûr', 'sûre')} de vouloir quitter la str ? T'es ${accord(currentPlayerGender, 'le fyot', 'la fyotte')} que tu penses être si tu fais ça... à bon entendrrr`)) {
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
            loadLeaderboard();
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