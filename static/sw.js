// Nexora AI - Service Worker
// Hii inawezesha app kuwa PWA na kufanya kazi offline

const CACHE_NAME = 'nexora-v1';
const urlsToCache = [
  '/',
  '/manifest.json',
  '/static/icon-512.png'
];

// ========== INSTALL EVENT ==========
self.addEventListener('install', event => {
  console.log('[Service Worker] Installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching app shell');
        return cache.addAll(urlsToCache);
      })
      .catch(err => {
        console.log('[Service Worker] Cache error:', err);
      })
  );
  
  // Force activate immediately
  self.skipWaiting();
});

// ========== ACTIVATE EVENT ==========
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating...');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  
  // Take control of all clients
  return self.clients.claim();
});

// ========== FETCH EVENT ==========
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }
  
  // Skip API requests - they need internet
  if (event.request.url.includes('/api/')) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        
        // Clone the request
        const fetchRequest = event.request.clone();
        
        return fetch(fetchRequest)
          .then(response => {
            // Check if valid response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response
            const responseToCache = response.clone();
            
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
            
            return response;
          })
          .catch(error => {
            console.log('[Service Worker] Fetch failed:', error);
            
            // Try to return offline page (optional)
            if (event.request.mode === 'navigate') {
              return caches.match('/');
            }
          });
      })
  );
});

// ========== NOTIFICATION PUSH (Optional) ==========
self.addEventListener('push', event => {
  const options = {
    body: event.data.text(),
    icon: '/static/icon-512.png',
    badge: '/static/icon-512.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    }
  };
  
  event.waitUntil(
    self.registration.showNotification('Nexora AI', options)
  );
});

// ========== BACKGROUND SYNC (Optional) ==========
self.addEventListener('sync', event => {
  if (event.tag === 'sync-messages') {
    console.log('[Service Worker] Background sync triggered');
    // You can add offline message sync here
  }
});
