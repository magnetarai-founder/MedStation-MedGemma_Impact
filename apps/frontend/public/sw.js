/**
 * ElohimOS Vault Service Worker
 * Provides offline support for vault files and UI
 */

const CACHE_VERSION = 'v1';
const CACHE_NAME = `elohimos-vault-${CACHE_VERSION}`;

// Assets to cache immediately
const STATIC_CACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json'
];

// Cache strategies
const CACHE_STRATEGIES = {
  CACHE_FIRST: 'cache-first',
  NETWORK_FIRST: 'network-first',
  NETWORK_ONLY: 'network-only',
  CACHE_ONLY: 'cache-only',
  STALE_WHILE_REVALIDATE: 'stale-while-revalidate'
};

// Route patterns and their strategies
const ROUTE_STRATEGIES = [
  { pattern: /\/api\/v1\/vault\/files\/.*\/download/, strategy: CACHE_STRATEGIES.NETWORK_FIRST },
  { pattern: /\/api\/v1\/vault\/files/, strategy: CACHE_STRATEGIES.NETWORK_FIRST },
  { pattern: /\/api\/v1\/vault\/folders/, strategy: CACHE_STRATEGIES.NETWORK_FIRST },
  { pattern: /\.(?:js|css|woff2?)$/, strategy: CACHE_STRATEGIES.CACHE_FIRST },
  { pattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/, strategy: CACHE_STRATEGIES.CACHE_FIRST }
];

// IndexedDB for offline operations queue
const DB_NAME = 'ElohimOSVault';
const DB_VERSION = 1;
const QUEUE_STORE = 'offlineQueue';
const CACHE_STORE = 'cacheMetadata';

/**
 * Install Event - Cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_CACHE_URLS);
    }).then(() => {
      console.log('[SW] Service worker installed');
      return self.skipWaiting();
    })
  );
});

/**
 * Activate Event - Clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Service worker activated');
      return self.clients.claim();
    })
  );
});

/**
 * Fetch Event - Handle network requests with appropriate caching strategy
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests for caching
  if (request.method !== 'GET') {
    // Queue POST/PUT/DELETE requests when offline
    if (!navigator.onLine) {
      event.respondWith(handleOfflineWrite(request));
    }
    return;
  }

  // Determine caching strategy for this request
  const strategy = getStrategyForRequest(url.pathname);

  event.respondWith(
    executeStrategy(request, strategy)
  );
});

/**
 * Message Event - Handle commands from clients
 */
self.addEventListener('message', (event) => {
  const { type, payload } = event.data;

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'CACHE_FILE':
      cacheFile(payload.url, payload.data);
      break;

    case 'CLEAR_CACHE':
      clearCache();
      break;

    case 'GET_CACHE_SIZE':
      getCacheSize().then((size) => {
        event.ports[0].postMessage({ size });
      });
      break;

    case 'SYNC_QUEUE':
      syncOfflineQueue();
      break;
  }
});

/**
 * Sync Event - Background sync for offline operations
 */
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-offline-queue') {
    console.log('[SW] Background sync triggered');
    event.waitUntil(syncOfflineQueue());
  }
});

/**
 * Get caching strategy for a request
 */
function getStrategyForRequest(pathname) {
  for (const route of ROUTE_STRATEGIES) {
    if (route.pattern.test(pathname)) {
      return route.strategy;
    }
  }
  return CACHE_STRATEGIES.NETWORK_FIRST; // Default strategy
}

/**
 * Execute caching strategy
 */
async function executeStrategy(request, strategy) {
  switch (strategy) {
    case CACHE_STRATEGIES.CACHE_FIRST:
      return cacheFirst(request);

    case CACHE_STRATEGIES.NETWORK_FIRST:
      return networkFirst(request);

    case CACHE_STRATEGIES.CACHE_ONLY:
      return cacheOnly(request);

    case CACHE_STRATEGIES.NETWORK_ONLY:
      return networkOnly(request);

    case CACHE_STRATEGIES.STALE_WHILE_REVALIDATE:
      return staleWhileRevalidate(request);

    default:
      return networkFirst(request);
  }
}

/**
 * Cache First Strategy
 */
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache first failed:', error);
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Network First Strategy
 */
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Cache Only Strategy
 */
async function cacheOnly(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  return new Response('Not in cache', { status: 404 });
}

/**
 * Network Only Strategy
 */
async function networkOnly(request) {
  return fetch(request);
}

/**
 * Stale While Revalidate Strategy
 */
async function staleWhileRevalidate(request) {
  const cachedResponse = await caches.match(request);

  const fetchPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      const cache = caches.open(CACHE_NAME);
      cache.then((c) => c.put(request, networkResponse.clone()));
    }
    return networkResponse;
  });

  return cachedResponse || fetchPromise;
}

/**
 * Handle offline write operations (POST/PUT/DELETE)
 */
async function handleOfflineWrite(request) {
  try {
    // Clone the request to read the body
    const clonedRequest = request.clone();
    const body = await clonedRequest.text();

    // Queue the operation
    await queueOfflineOperation({
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      body: body,
      timestamp: Date.now()
    });

    // Return success response
    return new Response(JSON.stringify({
      success: true,
      queued: true,
      message: 'Operation queued for sync when online'
    }), {
      status: 202,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('[SW] Failed to queue operation:', error);
    return new Response(JSON.stringify({
      success: false,
      error: 'Failed to queue operation'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Queue offline operation in IndexedDB
 */
async function queueOfflineOperation(operation) {
  const db = await openIndexedDB();
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  const store = tx.objectStore(QUEUE_STORE);

  await store.add({
    ...operation,
    id: `${Date.now()}-${Math.random()}`,
    status: 'pending'
  });

  await tx.complete;
  console.log('[SW] Operation queued:', operation.method, operation.url);
}

/**
 * Sync offline queue when back online
 */
async function syncOfflineQueue() {
  console.log('[SW] Syncing offline queue...');

  const db = await openIndexedDB();
  const tx = db.transaction(QUEUE_STORE, 'readonly');
  const store = tx.objectStore(QUEUE_STORE);
  const operations = await store.getAll();

  for (const operation of operations) {
    if (operation.status === 'pending') {
      try {
        const response = await fetch(operation.url, {
          method: operation.method,
          headers: operation.headers,
          body: operation.body
        });

        if (response.ok) {
          // Mark as synced
          const updateTx = db.transaction(QUEUE_STORE, 'readwrite');
          const updateStore = updateTx.objectStore(QUEUE_STORE);
          operation.status = 'synced';
          operation.syncedAt = Date.now();
          await updateStore.put(operation);
          await updateTx.complete;

          console.log('[SW] Operation synced:', operation.id);

          // Notify clients
          notifyClients({
            type: 'SYNC_SUCCESS',
            operation: operation
          });
        } else {
          throw new Error(`Sync failed: ${response.status}`);
        }
      } catch (error) {
        console.error('[SW] Failed to sync operation:', operation.id, error);

        // Mark as failed
        const updateTx = db.transaction(QUEUE_STORE, 'readwrite');
        const updateStore = updateTx.objectStore(QUEUE_STORE);
        operation.status = 'failed';
        operation.error = error.message;
        await updateStore.put(operation);
        await updateTx.complete;

        notifyClients({
          type: 'SYNC_FAILED',
          operation: operation,
          error: error.message
        });
      }
    }
  }

  console.log('[SW] Offline queue sync complete');
}

/**
 * Open IndexedDB
 */
function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // Create offline queue store
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        const queueStore = db.createObjectStore(QUEUE_STORE, { keyPath: 'id' });
        queueStore.createIndex('status', 'status', { unique: false });
        queueStore.createIndex('timestamp', 'timestamp', { unique: false });
      }

      // Create cache metadata store
      if (!db.objectStoreNames.contains(CACHE_STORE)) {
        const cacheStore = db.createObjectStore(CACHE_STORE, { keyPath: 'url' });
        cacheStore.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

/**
 * Cache a file manually
 */
async function cacheFile(url, data) {
  const cache = await caches.open(CACHE_NAME);
  const response = new Response(data);
  await cache.put(url, response);
  console.log('[SW] File cached:', url);
}

/**
 * Clear all caches
 */
async function clearCache() {
  await caches.delete(CACHE_NAME);
  console.log('[SW] Cache cleared');
}

/**
 * Get total cache size
 */
async function getCacheSize() {
  if ('storage' in navigator && 'estimate' in navigator.storage) {
    const estimate = await navigator.storage.estimate();
    return estimate.usage || 0;
  }
  return 0;
}

/**
 * Notify all clients
 */
async function notifyClients(message) {
  const clients = await self.clients.matchAll({ type: 'window' });
  clients.forEach((client) => {
    client.postMessage(message);
  });
}

console.log('[SW] Service worker script loaded');
