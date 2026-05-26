/**
 * Responsive Navigation & Layout Management
 * Handles mobile menu toggle, overlay interactions, and responsive adjustments
 */

document.addEventListener('DOMContentLoaded', function () {
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  if (!sidebarToggle || !sidebar || !sidebarOverlay) {
    return; // Skip if elements don't exist
  }

  /**
   * Toggle sidebar visibility on mobile
   */
  function toggleSidebar() {
    sidebar.classList.toggle('active');
    sidebarOverlay.classList.toggle('active');
    document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
  }

  /**
   * Close sidebar
   */
  function closeSidebar() {
    sidebar.classList.remove('active');
    sidebarOverlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  // Sidebar toggle button
  sidebarToggle.addEventListener('click', toggleSidebar);

  // Close sidebar when clicking overlay
  sidebarOverlay.addEventListener('click', closeSidebar);

  // Close sidebar when clicking links inside it
  const sidebarLinks = sidebar.querySelectorAll('a');
  sidebarLinks.forEach((link) => {
    link.addEventListener('click', closeSidebar);
  });

  // Close sidebar on Escape key
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sidebar.classList.contains('active')) {
      closeSidebar();
    }
  });

  /**
   * Handle window resize - reset sidebar on desktop view
   */
  let resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (window.innerWidth > 767) {
        closeSidebar();
      }
    }, 250);
  });

  /**
   * Adjust chat height based on viewport
   */
  function adjustChatHeight() {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;

    if (window.innerWidth <= 767) {
      chatMessages.style.height = '300px';
    } else if (window.innerWidth <= 1024) {
      chatMessages.style.height = '400px';
    } else {
      chatMessages.style.height = '420px';
    }
  }

  adjustChatHeight();
  window.addEventListener('resize', adjustChatHeight);

  /**
   * Ensure proper scroll behavior on mobile
   */
  const scrollables = document.querySelectorAll('[id*="chat-messages"], .table-responsive');
  scrollables.forEach((el) => {
    el.addEventListener('touchstart', function () {
      this.style.scrollBehavior = 'smooth';
    });
  });

  /**
   * Handle dropdown menu positioning on mobile
   */
  function handleDropdownPosition() {
    const dropdowns = document.querySelectorAll('.account-menu, .dropdown-menu');
    dropdowns.forEach((dropdown) => {
      const trigger = dropdown.previousElementSibling;
      if (!trigger) return;

      // Adjust dropdown position on mobile to prevent overflow
      if (window.innerWidth <= 480) {
        dropdown.style.right = '0';
        dropdown.style.left = 'auto';
      }
    });
  }

  handleDropdownPosition();
  window.addEventListener('resize', handleDropdownPosition);

  /**
   * Add touch support for sidebar swipe
   */
  let touchStartX = 0;
  let touchEndX = 0;

  document.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
  });

  document.addEventListener('touchend', (e) => {
    touchEndX = e.changedTouches[0].screenX;
    handleSwipe();
  });

  function handleSwipe() {
    const swipeThreshold = 50;
    const diff = touchStartX - touchEndX;

    // Swipe left to open sidebar
    if (diff > swipeThreshold && !sidebar.classList.contains('active') && window.innerWidth <= 767) {
      toggleSidebar();
    }

    // Swipe right to close sidebar
    if (diff < -swipeThreshold && sidebar.classList.contains('active')) {
      closeSidebar();
    }
  }

  /**
   * Utility function to check if mobile
   */
  window.isMobile = function () {
    return window.innerWidth <= 767;
  };

  /**
   * Utility function to check if tablet
   */
  window.isTablet = function () {
    return window.innerWidth > 767 && window.innerWidth <= 1024;
  };

  /**
   * Utility function to check if desktop
   */
  window.isDesktop = function () {
    return window.innerWidth > 1024;
  };

  /**
   * Handle form input focus to show virtual keyboard hints on mobile
   */
  const formInputs = document.querySelectorAll('input[type="text"], input[type="email"], input[type="password"], textarea');
  formInputs.forEach((input) => {
    input.addEventListener('focus', function () {
      if (window.isMobile()) {
        // Scroll input into view on mobile
        setTimeout(() => {
          this.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 300);
      }
    });
  });

  /**
   * Initialize Bootstrap tooltips on mobile-friendly elements
   */
  if (typeof bootstrap !== 'undefined') {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  console.log('Responsive navigation initialized');
});

/**
 * Prevent layout shift on mobile
 */
if ('scrollRestoration' in window.history) {
  window.history.scrollRestoration = 'manual';
}
