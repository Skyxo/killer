// Elements DOM
const loginContainer = document.getElementById('login-container');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const playerContainer = document.getElementById('player-container');
const playerNicknameHeader = document.getElementById('player-nickname-header');
const playerPersonPhoto = document.getElementById('player-person-photo');
const playerFeetPhoto = document.getElementById('player-feet-photo');
const playerPersonPhotoContainer = document.getElementById('player-person-photo-container');
const playerFeetPhotoContainer = document.getElementById('player-feet-photo-container');
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

// Sons de pet disponibles
const petSounds = [
    './client/sounds/pet_024.mp3',
    './client/sounds/sf_pet_10.mp3',
    './client/sounds/sf_pet_11.mp3',
    './client/sounds/sf_pet_12.mp3',
    './client/sounds/sf_pet_13.mp3',
    './client/sounds/sf_pet_long.mp3',
    './client/sounds/sf_rot_pet_03.mp3'
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
    modalImage.src = imageSrc;
    photoModal.classList.remove('hidden');
}

// Fonction pour fermer la modal
function closePhotoModal() {
    photoModal.classList.add('hidden');
}

// Vérifier si l'utilisateur est connecté au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    checkLoggedIn();
    
    // Ajouter l'événement de clic sur le logo U56
    const logo = document.querySelector('.logo');
    if (logo) {
        logo.addEventListener('click', playRandomPetSound);
        logo.style.cursor = 'pointer'; // Changer le curseur pour indiquer que c'est cliquable
    }
    
    // Configurer les événements pour la modale des photos
    playerPersonPhoto.addEventListener('click', () => openPhotoModal(playerPersonPhoto.src));
    targetPersonPhoto.addEventListener('click', () => openPhotoModal(targetPersonPhoto.src));
    targetFeetPhoto.addEventListener('click', () => openPhotoModal(targetFeetPhoto.src));
    
    // Fermer la modale
    closeModal.addEventListener('click', closePhotoModal);
    photoModal.addEventListener('click', (event) => {
        if (event.target === photoModal) {
            closePhotoModal();
        }
    });
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
            if (!response.ok) {
                throw new Error('Non connecté');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showPlayerInterface(data);
            } else {
                showLoginForm();
            }
        })
        .catch(() => {
            // Si erreur, montrer le formulaire de connexion
            showLoginForm();
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
    playerContainer.classList.add('hidden');
    loginContainer.classList.remove('hidden');
    loginForm.reset();
    loginError.textContent = '';
}

/**
 * Affiche l'interface du joueur avec ses informations et sa cible
 */
function showPlayerInterface(data) {
    loginContainer.classList.add('hidden');
    playerContainer.classList.remove('hidden');
    
    // Informations du joueur
    playerNicknameHeader.textContent = data.player.nickname;
    
    // Gérer l'état du joueur (mort, vivant, abandonné)
    if (data.player.status && data.player.status.toLowerCase() === "dead") {
        // Le joueur est mort, désactiver les boutons
        killedBtn.disabled = true;
        giveUpBtn.disabled = true;
        playerContainer.classList.add('player-dead');
    } else if (data.player.status && data.player.status.toLowerCase() === "gaveup") {
        // Le joueur a abandonné, désactiver les boutons
        killedBtn.disabled = true;
        giveUpBtn.disabled = true;
        playerContainer.classList.add('player-gave-up');
    } else {
        // Le joueur est vivant, activer les boutons
        killedBtn.disabled = false;
        giveUpBtn.disabled = false;
        playerContainer.classList.remove('player-dead');
        playerContainer.classList.remove('player-gave-up');
    }
    
    // Photos du joueur
    if (data.player.person_photo) {
        // Utiliser le format d'intégration d'image Google Drive
        playerPersonPhoto.src = `https://drive.google.com/thumbnail?id=${data.player.person_photo}&sz=w500`;
        playerPersonPhotoContainer.classList.remove('hidden');
    } else {
        playerPersonPhotoContainer.classList.add('hidden');
    }
    
    if (data.player.feet_photo) {
        // Utiliser le format d'intégration d'image Google Drive
        playerFeetPhoto.src = `https://drive.google.com/thumbnail?id=${data.player.feet_photo}&sz=w500`;
        playerFeetPhotoContainer.classList.remove('hidden');
    } else {
        playerFeetPhotoContainer.classList.add('hidden');
    }
    
    // Informations de la cible
    if (data.target) {
        updateTargetInfo(data.target);
        targetCard.classList.remove('hidden');
        noTargetMessage.classList.add('hidden');
    } else {
        targetCard.classList.add('hidden');
        noTargetMessage.classList.remove('hidden');
    }
}

/**
 * Met à jour les informations de la cible dans l'interface
 */
function updateTargetInfo(target) {
    targetNickname.textContent = target.nickname;
    targetAction.textContent = target.action;
    
    // Photos de la cible
    if (target.person_photo) {
        // Utiliser le format d'intégration d'image Google Drive
        targetPersonPhoto.src = `https://drive.google.com/thumbnail?id=${target.person_photo}&sz=w500`;
        targetPersonPhotoContainer.classList.remove('hidden');
    } else {
        targetPersonPhotoContainer.classList.add('hidden');
    }
    
    if (target.feet_photo) {
        // Utiliser le format d'intégration d'image Google Drive
        targetFeetPhoto.src = `https://drive.google.com/thumbnail?id=${target.feet_photo}&sz=w500`;
        targetFeetPhotoContainer.classList.remove('hidden');
    } else {
        targetFeetPhotoContainer.classList.add('hidden');
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
        } else {
            alert(`Erreur: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        alert('Erreur de communication avec le serveur');
    });
}