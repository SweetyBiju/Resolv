// Dashboard functionality

let currentUser = null;
let groups = [];
let settlements = [];

// Initialize app
async function initApp() {
    // Require authentication
    if (!auth.requireAuth()) {
        return;
    }

    // Initialize UI components
    ui.initTheme();
    ui.setupInviteCodeInput();
    ui.setupCopyCodeButtons();

    // Setup event listeners
    setupEventListeners();

    // Load initial data
    await loadDashboardData();
}

// Setup all event listeners
function setupEventListeners() {
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            auth.logout();
        });
    }

    // Create group button
    const createGroupBtn = document.getElementById('createGroupBtn');
    if (createGroupBtn) {
        createGroupBtn.addEventListener('click', () => {
            ui.showModal('createGroupModal');
        });
    }

    // Join group button
    const joinGroupBtn = document.getElementById('joinGroupBtn');
    if (joinGroupBtn) {
        joinGroupBtn.addEventListener('click', () => {
            ui.showModal('joinGroupModal');
        });
    }

    // Cancel buttons
    const cancelCreateGroup = document.getElementById('cancelCreateGroup');
    if (cancelCreateGroup) {
        cancelCreateGroup.addEventListener('click', () => {
            ui.hideModal('createGroupModal');
        });
    }

    const cancelJoinGroup = document.getElementById('cancelJoinGroup');
    if (cancelJoinGroup) {
        cancelJoinGroup.addEventListener('click', () => {
            ui.hideModal('joinGroupModal');
        });
    }

    // Create group form
    const createGroupForm = document.getElementById('createGroupForm');
    if (createGroupForm) {
        createGroupForm.addEventListener('submit', handleCreateGroup);
    }

    // Join group form
    const joinGroupForm = document.getElementById('joinGroupForm');
    if (joinGroupForm) {
        joinGroupForm.addEventListener('submit', handleJoinGroup);
    }

    // Refresh groups button
    const refreshGroupsBtn = document.getElementById('refreshGroupsBtn');
    if (refreshGroupsBtn) {
        refreshGroupsBtn.addEventListener('click', async () => {
            refreshGroupsBtn.classList.add('animate-spin');
            await loadGroups();
            refreshGroupsBtn.classList.remove('animate-spin');
        });
    }

    // Add expense button
    const addExpenseBtn = document.getElementById('addExpenseBtn');
    if (addExpenseBtn) {
        addExpenseBtn.addEventListener('click', () => {
            utils.showToast('Add expense feature coming soon!', 'info');
        });
    }

    // Confirm settlement buttons (delegated)
    document.addEventListener('click', async (e) => {
        const confirmBtn = e.target.closest('.confirm-settlement-btn');
        if (confirmBtn) {
            const settlementId = parseInt(confirmBtn.dataset.settlementId);
            await handleConfirmSettlement(settlementId);
        }
    });

    // Group card clicks (delegated)
    document.addEventListener('click', (e) => {
        const groupCard = e.target.closest('[data-group-id]');
        if (groupCard && !e.target.closest('.copy-code-btn')) {
            const groupId = parseInt(groupCard.dataset.groupId);
            handleGroupClick(groupId);
        }
    });
}

// Load all dashboard data
async function loadDashboardData() {
    ui.showLoadingOverlay();

    try {
        // Load user data
        currentUser = await auth.getCurrentUser();
        ui.displayUserInfo(currentUser);

        // Load groups
        await loadGroups();

        // Load settlements
        await loadSettlements();

        // Show demo mode notice if active
        if (api.demoMode) {
            utils.showToast('Demo mode active - using sample data', 'info', 5000);
        }
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        utils.showToast('Failed to load data', 'error');
    } finally {
        ui.hideLoadingOverlay();
    }
}

// Load groups
async function loadGroups() {
    const groupsList = document.getElementById('groupsList');
    if (!groupsList) return;

    try {
        groups = await api.getGroups();

        if (groups.length === 0) {
            groupsList.innerHTML = ui.renderEmptyState('No groups yet. Create or join one to get started!', 'users');
        } else {
            groupsList.innerHTML = groups.map(group => ui.renderGroupCard(group)).join('');
        }

        // Re-initialize Lucide icons
        if (window.lucide) {
            lucide.createIcons();
        }
    } catch (error) {
        console.error('Failed to load groups:', error);
        groupsList.innerHTML = ui.renderEmptyState('Failed to load groups', 'alert-circle');
    }
}

// Load settlements
async function loadSettlements() {
    const settlementsList = document.getElementById('settlementsList');
    if (!settlementsList) return;

    try {
        settlements = await api.getSettlements();

        // Filter pending settlements
        const pendingSettlements = settlements.filter(s => s.status === 'pending');

        if (pendingSettlements.length === 0) {
            settlementsList.innerHTML = ui.renderEmptyState('No pending settlements', 'check-circle');
        } else {
            settlementsList.innerHTML = pendingSettlements.map(settlement => ui.renderSettlementCard(settlement)).join('');
        }

        // Re-initialize Lucide icons
        if (window.lucide) {
            lucide.createIcons();
        }
    } catch (error) {
        console.error('Failed to load settlements:', error);
        settlementsList.innerHTML = ui.renderEmptyState('Failed to load settlements', 'alert-circle');
    }
}

// Handle create group form submission
async function handleCreateGroup(e) {
    e.preventDefault();

    const groupName = document.getElementById('groupName').value;
    const groupDescription = document.getElementById('groupDescription').value;

    try {
        const newGroup = await api.createGroup({
            name: groupName,
            description: groupDescription
        });

        utils.showToast('Group created successfully!', 'success');
        utils.hapticFeedback([10, 30, 10]);

        ui.hideModal('createGroupModal');
        document.getElementById('createGroupForm').reset();

        // Reload groups
        await loadGroups();

        // Show invite code
        setTimeout(() => {
            utils.showToast(`Invite code: ${newGroup.invite_code}`, 'info', 5000);
        }, 500);

    } catch (error) {
        console.error('Failed to create group:', error);
        utils.showToast('Failed to create group', 'error');
    }
}

// Handle join group form submission
async function handleJoinGroup(e) {
    e.preventDefault();

    const inviteCode = document.getElementById('inviteCode').value;

    if (!utils.validateInviteCode(inviteCode)) {
        utils.showToast('Invalid invite code format', 'error');
        return;
    }

    try {
        await api.joinGroup(inviteCode);

        utils.showToast('Successfully joined group!', 'success');
        utils.hapticFeedback([10, 30, 10]);

        ui.hideModal('joinGroupModal');
        document.getElementById('joinGroupForm').reset();

        // Reload groups
        await loadGroups();

    } catch (error) {
        console.error('Failed to join group:', error);
        utils.showToast('Failed to join group. Check the invite code.', 'error');
    }
}

// Handle confirm settlement
async function handleConfirmSettlement(settlementId) {
    const settlement = settlements.find(s => s.id === settlementId);
    if (!settlement) return;

    utils.confirm(
        `Confirm that you received ${utils.formatCurrency(settlement.amount)} from ${settlement.from_user.name}?`,
        async () => {
            try {
                await api.confirmSettlement(settlementId);

                utils.showToast('Settlement confirmed!', 'success');
                utils.hapticFeedback([10, 30, 10]);

                // Calculate and update reliability score
                const oldScore = currentUser.reliability_score || 0;
                const newScore = utils.calculateScoreIncrease(oldScore);

                // Update score in auth
                await auth.updateReliabilityScore(newScore);
                currentUser.reliability_score = newScore;

                // Animate score increase
                ui.updateReliabilityScore(Math.round(oldScore), Math.round(newScore));

                // Reload settlements after a delay to show confetti
                setTimeout(async () => {
                    await loadSettlements();
                }, 1000);

            } catch (error) {
                console.error('Failed to confirm settlement:', error);
                utils.showToast('Failed to confirm settlement', 'error');
            }
        }
    );
}

// Handle group card click
function handleGroupClick(groupId) {
    const group = groups.find(g => g.id === groupId);
    if (!group) return;

    // Show group details modal (simplified for now)
    utils.showToast(`Group: ${group.name}`, 'info');

    // In a real app, this would navigate to a group details page
    console.log('Navigate to group details:', groupId);
}

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initApp,
        loadGroups,
        loadSettlements,
        handleCreateGroup,
        handleJoinGroup,
        handleConfirmSettlement
    };
}
