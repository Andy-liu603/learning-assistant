/* IndexedDB 对话持久化存储 */
const DB_NAME = 'ai_learning_chat';
const DB_VERSION = 1;

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = e => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('chats')) {
        db.createObjectStore('chats', { keyPath: 'id' });
      }
    };
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = e => reject(e.target.error);
  });
}

/**
 * 保存对话
 * @param {string} id - 对话标识（固定 'current' 表示当前对话）
 * @param {object} data - { messages: [], convId, docId, model }
 */
export async function saveChat(data) {
  try {
    const db = await openDB();
    const tx = db.transaction('chats', 'readwrite');
    const store = tx.objectStore('chats');
    store.put({ id: 'current', ...data, updatedAt: Date.now() });
    return new Promise(resolve => { tx.oncomplete = () => resolve(); });
  } catch (e) {
    console.warn('ChatDB save failed:', e);
  }
}

/**
 * 读取当前对话
 */
export async function loadChat() {
  try {
    const db = await openDB();
    const tx = db.transaction('chats', 'readonly');
    const store = tx.objectStore('chats');
    const req = store.get('current');
    return new Promise((resolve, reject) => {
      req.onsuccess = e => resolve(e.target.result || null);
      req.onerror = e => reject(e.target.error);
    });
  } catch (e) {
    console.warn('ChatDB load failed:', e);
    return null;
  }
}

/**
 * 清除当前对话
 */
export async function clearChat() {
  try {
    const db = await openDB();
    const tx = db.transaction('chats', 'readwrite');
    tx.objectStore('chats').delete('current');
    return new Promise(resolve => { tx.oncomplete = () => resolve(); });
  } catch (e) {
    console.warn('ChatDB clear failed:', e);
  }
}
