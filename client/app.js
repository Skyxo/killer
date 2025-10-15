// Elements DOM
const loginContainer = document.getElementById('login-container');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const playerContainer = document.getElementById('player-container');
const playerName = document.getElementById('player-name');
const playerFirstname = document.getElementById('player-firstname');
const playerNickname = document.getElementById('player-nickname');
const playerYear = document.getElementById('player-year');
const targetName = document.getElementById('target-name');
const targetFirstname = document.getElementById('target-firstname');
const targetNickname = document.getElementById('target-nickname');
const targetYear = document.getElementById('target-year');
const targetAction = document.getElementById('target-action');
const targetCard = document.getElementById('target-card');
const noTargetMessage = document.getElementById('no-target-message');
const killBtn = document.getElementById('kill-btn');
const logoutBtn = document.getElementById('logout-btn');
const killNotification = document.getElementById('kill-notification');
const newTargetName = document.getElementById('new-target-name');
const newTargetAction = document.getElementById('new-target-action');
const closeNotification = document.getElementById('close-notification');

// Vérifier si l'utilisateur est connecté au chargement de la page
document.addEventListener('DOMContentLoaded', checkLoggedIn);

// Event Listeners
loginForm.addEventListener('submit', handleLogin);
killBtn.addEventListener('submit', handleKill);
killBtn.addEventListener('click', handleKill);
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
 * Gère l'action de tuer une cible
 */
function handleKill(e) {
    e.preventDefault();
    
    // Confirmation avant de procéder
    if (!confirm("Êtes-vous sûr d'avoir éliminé votre cible ? Cette action ne peut pas être annulée.")) {
        return;
    }
    
    fetch('/api/kill', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Afficher la notification de kill réussi
            if (data.target) {
                newTargetName.textContent = `${data.target.firstname} ${data.target.name} (${data.target.nickname})`;
                newTargetAction.textContent = data.target.action;
                
                // Mettre à jour les informations de la cible dans l'interface
                updateTargetInfo(data.target);
            } else {
                newTargetName.textContent = "Aucune cible disponible";
                newTargetAction.textContent = "Le jeu est peut-être terminé";
                
                // Cacher la carte de la cible et afficher le message
                targetCard.classList.add('hidden');
                noTargetMessage.classList.remove('hidden');
            }
            
            // Afficher la notification
            killNotification.classList.remove('hidden');
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
    playerName.textContent = data.player.name;
    playerFirstname.textContent = data.player.firstname;
    playerNickname.textContent = data.player.nickname;
    playerYear.textContent = data.player.year;
    
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
    targetName.textContent = target.name;
    targetFirstname.textContent = target.firstname;
    targetNickname.textContent = target.nickname;
    targetYear.textContent = target.year;
    targetAction.textContent = target.action;
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