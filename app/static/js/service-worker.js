// service-worker.js - Updated to improve push notification support
const CACHE_NAME = 'gps-tracking-cache-v2';
const urlsToCache = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/img/logo.png',
  '/static/img/badge.png',
  'https://cdn.socket.io/4.5.4/socket.io.min.js',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js'
];

// Install Service Worker
self.addEventListener('install', event => {
  console.log('Service Worker installing...');
  self.skipWaiting();
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache opened');
        return cache.addAll(urlsToCache);
      })
  );
});

// Activate Service Worker
self.addEventListener('activate', event => {
  console.log('Service Worker activated');
  
  event.waitUntil(clients.claim());
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Tracking data
let trackingData = {
  orderId: null,
  role: null,
  position: null,
  lastUpdate: null
};

// Listen for messages from client
self.addEventListener('message', event => {
  const data = event.data;
  
  if (data.action === 'startTracking') {
    trackingData = {
      orderId: data.orderId,
      role: data.role,
      position: data.position,
      lastUpdate: Date.now()
    };
    startBackgroundTracking();
    event.source.postMessage({ type: 'trackingStarted', timestamp: Date.now() });
  } else if (data.action === 'updatePosition') {
    trackingData.position = data.position;
    trackingData.lastUpdate = Date.now();
  } else if (data.action === 'stopTracking') {
    stopBackgroundTracking();
    event.source.postMessage({ type: 'trackingStopped', timestamp: Date.now() });
  } else if (data.action === 'ping') {
    event.source.postMessage({ type: 'pong', timestamp: Date.now() });
  }
});

const BACKGROUND_SYNC_INTERVAL = 15000;
let backgroundSyncIntervalId = null;

function startBackgroundTracking() {
  if (backgroundSyncIntervalId) clearInterval(backgroundSyncIntervalId);
  
  syncLocation();
  backgroundSyncIntervalId = setInterval(syncLocation, BACKGROUND_SYNC_INTERVAL);
  console.log('Background tracking started');
}

function stopBackgroundTracking() {
  if (backgroundSyncIntervalId) {
    clearInterval(backgroundSyncIntervalId);
    backgroundSyncIntervalId = null;
  }
  
  trackingData = { orderId: null, role: null, position: null, lastUpdate: null };
  console.log('Background tracking stopped');
}

function syncLocation() {
  if (!trackingData.position || !trackingData.orderId) return;
  
  const timeSinceLastUpdate = Date.now() - trackingData.lastUpdate;
  if (timeSinceLastUpdate < 120000) {
    fetch('/api/update-location', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        order_id: trackingData.orderId,
        lat: trackingData.position.lat,
        lon: trackingData.position.lon,
        accuracy: trackingData.position.accuracy,
        role: trackingData.role,
        timestamp: Date.now(),
        background: true
      })
    })
    .then(response => {
      if (response.ok) {
        console.log('Location synced from Service Worker');
        self.clients.matchAll().then(clients => {
          clients.forEach(client => {
            client.postMessage({ type: 'syncSuccess', timestamp: Date.now() });
          });
        });
      }
    })
    .catch(error => console.error('Error syncing location:', error));
  }
}

// Handle push notifications
self.addEventListener('push', event => {
  console.log('Push received:', event);
  
  let notificationData;
  try {
    notificationData = event.data.json();
  } catch (e) {
    notificationData = {
      title: 'Notificación',
      body: 'Nueva actualización disponible',
      data: {}
    };
  }
  
  const title = notificationData.title || 'Notificación';
  const options = {
    body: notificationData.body || 'Nueva actualización',
    icon: notificationData.icon || '/static/img/logo.png',
    badge: notificationData.badge || '/static/img/badge.png',
    vibrate: notificationData.vibrate || [200, 100, 200],
    data: notificationData.data || {},
    tag: notificationData.tag || `order-${notificationData.data.orderId || 'default'}`
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
      .then(() => console.log('Notification shown:', title))
      .catch(error => console.error('Error showing notification:', error))
  );
});

// Handle notification click
self.addEventListener('notificationclick', event => {
  console.log('Notification clicked:', event);
  
  event.notification.close();
  
  const notificationData = event.notification.data || {};
  const url = notificationData.url || `/dashboard/cliente/ordenes/orden/${notificationData.orderId || ''}`;
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        for (let client of windowClients) {
          if (client.url === url && 'focus' in client) return client.focus();
        }
        if (clients.openWindow) return clients.openWindow(url);
      })
  );
});