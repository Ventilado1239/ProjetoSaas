import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: true,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string | null) => void; reject: (error: Error) => void }> = [];

const processQueue = (error: Error | null, token: string | null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  failedQueue = [];
};

const refreshToken = async () => {
  await axios.post(
    `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/auth/refresh`,
    {},
    { withCredentials: true }
  );
};

const logout = () => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('auth-failed'));
  }
};

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise<string | null>((resolve, reject) => {
          failedQueue.push({ 
            resolve: (token) => resolve(token), 
            reject: (err) => reject(err) 
          });
        }).then(() => api(originalRequest));
      }
      
      originalRequest._retry = true;
      isRefreshing = true;
      
      try {
        await refreshToken();
        processQueue(null, null);
        return api(originalRequest);
      } catch (err) {
        processQueue(err as Error, null);
        logout();
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
