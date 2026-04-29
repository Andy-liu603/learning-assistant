/* API 请求封装 */

const API_BASE = '/api';

function getToken() {
  return localStorage.getItem('access_token');
}

async function request(endpoint, options = {}) {
  const { method = 'GET', body, params, formData } = options;
  const token = getToken();

  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let url = `${API_BASE}${endpoint}`;
  if (params) {
    url += '?' + new URLSearchParams(params).toString();
  }

  const fetchOptions = { method, headers };

  if (formData) {
    fetchOptions.body = formData;
  } else if (body) {
    headers['Content-Type'] = 'application/json';
    fetchOptions.body = JSON.stringify(body);
  }

  const response = await fetch(url, fetchOptions);

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.hash = '#/login';
    throw new Error('未登录或登录已过期');
  }

  if (response.status >= 500) {
    throw new Error('服务器错误');
  }

  return response.json();
}

export const api = {
  get: (url, params) => request(url, { method: 'GET', params }),
  post: (url, body) => request(url, { method: 'POST', body }),
  put: (url, body) => request(url, { method: 'PUT', body }),
  delete: (url) => request(url, { method: 'DELETE' }),
  upload: (url, formData) => request(url, { method: 'POST', formData }),

  /** 下载文件 */
  download(url) {
    const token = getToken();
    const a = document.createElement('a');
    a.href = `${API_BASE}${url}`;
    if (token) {
      // 通过 fetch 下载，以便注入 Authorization 头
      fetch(a.href, { headers: { 'Authorization': `Bearer ${token}` } })
        .then(r => r.blob())
        .then(blob => {
          const blobUrl = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = blobUrl;
          link.download = '';
          link.click();
          URL.revokeObjectURL(blobUrl);
        });
    } else {
      a.click();
    }
  },

  /** SSE 流式请求 - 返回 AbortController 用于取消 */
  stream(url, body, onChunk, onDone, onError) {
    const token = getToken();
    const controller = new AbortController();

    fetch(`${API_BASE}${url}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(body),
      signal: controller.signal
    }).then(async response => {
      if (!response.ok) {
        onError(new Error(`HTTP ${response.status}`));
        return;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.done) { onDone(data); return; }
              if (data.error) { onError(new Error(data.error)); return; }
              if (data.chunk) { onChunk(data.chunk); }
            } catch (e) { /* skip malformed chunks */ }
          }
        }
      }
      onDone({});
    }).catch(err => {
      if (err.name !== 'AbortError') {
        onError(err);
      }
    });

    return controller;
  }
};

export { API_BASE, getToken };
