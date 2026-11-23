document.addEventListener('DOMContentLoaded', () => {
  const navButtons = document.querySelectorAll('.nav-btn');
  const pages = document.querySelectorAll('.page');
  const pageTitle = document.getElementById('page-title');

  navButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const title = btn.getAttribute('data-title');

      // Update active button
      navButtons.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      // Switch visible page
      pages.forEach((page) => {
        page.classList.toggle('active', page.id === targetId);
      });

      // Update header title
      pageTitle.textContent = title;
      window.scrollTo(0, 0);
    });
  });

  // Register Service Worker for PWA support
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js').catch((err) => {
      console.error('Service Worker registration failed:', err);
    });
  }
});
