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
let currentTrombiCategory = 'all';

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

function updateTrombiCategoryButtons() {
    const categoryButtons = document.querySelectorAll('.trombi-category-btn');
    
    categoryButtons.forEach(btn => {
        const category = btn.dataset.category;
        
        if (currentPlayerIsAdmin) {
            // Pour les admins : afficher les catégories admin, cacher les catégories non-admin
            if (btn.classList.contains('admin-only')) {
                btn.style.display = '';
                btn.classList.remove('hidden');
            } else if (btn.classList.contains('non-admin-only')) {
                btn.style.display = 'none';
                btn.classList.add('hidden');
            }
        } else {
            // Pour les non-admins : afficher les catégories non-admin, cacher les catégories admin
            if (btn.classList.contains('non-admin-only')) {
                btn.style.display = '';
                btn.classList.remove('hidden');
            } else if (btn.classList.contains('admin-only')) {
                btn.style.display = 'none';
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
        if (currentTrombiCategory === 'all') {
            return true;
        } else if (currentTrombiCategory === 'alive') {
            const status = (player.status || 'alive').toLowerCase();
            // Exclure les admins de la catégorie "vivants"
            return status === 'alive' && !player.is_admin;
        } else if (currentTrombiCategory === 'dead') {
            const status = (player.status || 'alive').toLowerCase();
            // Pour la catégorie "Morts", ne plus inclure les abandons
            return status === 'dead';
        } else if (currentTrombiCategory === 'gaveup') {
            const status = (player.status || 'alive').toLowerCase();
            // Catégorie "Abandons" - uniquement pour les admins
            return status === 'gaveup';
        } else if (currentTrombiCategory === 'players') {
            // Catégorie "Joueurs" pour les non-admins : tous les joueurs (y compris les admins)
            return true;
        } else if (currentTrombiCategory === 'admins') {
            // Catégorie "Admins" pour les non-admins : seulement les admins
            return player.is_admin;
        }
        return true;
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
        if (currentPlayerIsAdmin && !player.is_admin) {
            const statusChip = document.createElement('span');
            
            // Afficher le statut uniquement pour les non-admins
            if (typeof player.status === 'string' && player.status) {
                const normalizedStatus = player.status.toLowerCase();
                statusChip.classList.add('status-pill', `status-${normalizedStatus}`);
                statusChip.textContent = getStatusLabel(normalizedStatus);
            }
            
            if (statusChip.textContent) {
                labelWrapper.appendChild(statusChip);
            }
        }

        if (player.is_admin) {
            labelWrapper.appendChild(createAdminBadge());
        }

        entryButton.appendChild(labelWrapper);

        // Afficher le nombre de kills à droite pour les admins
        if (currentPlayerIsAdmin && !player.is_admin) {
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

    // Affichage du badge de statut pour les admins (sur la même ligne que le nom)
    // Les admins (joueurs avec is_admin=true) n'ont PAS de badge de statut car ils ne participent pas au jeu
    if (currentPlayerIsAdmin && !player.is_admin) {
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
        title.appendChild(createAdminBadge());
    }

    trombiDetails.appendChild(title);

    // Afficher le message info après le statut selon le type de joueur
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
                message = `${accord(player.gender, 'Ce (gros) fyot pense', 'Cette grosse fyotte pense')} qu'il y a ${kroAnswer} ${quartWord} dans une krô`;
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

    // Afficher la cible et l'action pour les admins (dans le metaContainer)
    if (currentPlayerIsAdmin && player.target) {
        const targetInfoMeta = document.createElement('span');
        targetInfoMeta.classList.add('trombi-target-info-meta');
        
        let targetMessage = `doit kill ${player.target}`;
        if (player.action) {
            targetMessage += ` : "${player.action}"`;
        }
        
        targetInfoMeta.textContent = targetMessage;
        metaContainer.appendChild(targetInfoMeta);
        metaHasContent = true;
    }

    // Afficher les statistiques pour les admins (entre le message de kill et la photo)
    if (currentPlayerIsAdmin) {
        const statsContainer = document.createElement('div');
        statsContainer.classList.add('trombi-admin-stats');
        
        // Ne pas afficher les statistiques de kill pour les admins (ils ne participent pas au jeu)
        if (!player.is_admin) {
            // Nombre de kills
            const killCount = player.kill_count || 0;
            const killsText = document.createElement('p');
            killsText.classList.add('trombi-stat-item');
            killsText.innerHTML = `<strong>Kills :</strong> ${killCount}`;
            statsContainer.appendChild(killsText);
            
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
                const eliminationOrder = player.elimination_order || 0;
                
                // N = nombre total de joueurs de la partie (ceux avec elimination_order !== -1)
                const totalActivePlayers = trombiPlayers.filter(p => {
                    const order = p.elimination_order;
                    return order !== undefined && order !== null && order !== -1;
                }).length;
                
                const orderText = document.createElement('p');
                orderText.classList.add('trombi-stat-item');
                // Format : "Mort en 1er (1/15)" ou "Mort en 5ème (5/15)"
                orderText.innerHTML = `<strong>Mort en ${getOrdinal(eliminationOrder)}</strong> (${eliminationOrder}/${totalActivePlayers})`;
                statsContainer.appendChild(orderText);
            }
        }
        
        metaContainer.appendChild(statsContainer);
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
        
        // Compter les joueurs vivants : ceux avec status === 'alive' ET qui ne sont pas admins
        const aliveCount = (data.leaderboard || []).filter(player => {
            return player.status === 'alive' && !player.is_admin;
        }).length;
        
        // Afficher "Il reste X joueurs en vie" pour tout le monde
        if (leaderboardRemaining) {
            const remainingText = `Il reste ${aliveCount} joueur${aliveCount > 1 ? 's' : ''} en vie`;
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
        
        // Ajouter le joueur actuel s'il n'est pas dans le leaderboard et n'est pas admin
        let playersToDisplay = [...playersWithKills];
        if (currentPlayer && !currentPlayer.is_admin) {
            const isInLeaderboard = playersWithKills.some(p => 
                p.nickname && p.nickname.toLowerCase() === currentPlayerNickname.toLowerCase()
            );
            
            if (!isInLeaderboard) {
                // Ajouter le joueur actuel à la fin
                playersToDisplay.push(currentPlayer);
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
            renderLeaderboard(playersToDisplay);
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
        
        // Vérifier si c'est le joueur actuel
        const isCurrentPlayer = player.nickname && currentPlayerNickname && 
            player.nickname.toLowerCase() === currentPlayerNickname.toLowerCase();
        
        if (isCurrentPlayer) {
            entry.classList.add('leaderboard-entry-current');
        }
        
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
    if (currentPlayerIsAdmin) {
        currentTrombiCategory = 'all';
    } else {
        currentTrombiCategory = 'players';
    }
    
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
    if (!confirm(`Êtes-vous ${accord(currentPlayerGender, 'sûr', 'sûre')} de vouloir abandonner le jeu ? Cette action ne peut pas être annulée.`)) {
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