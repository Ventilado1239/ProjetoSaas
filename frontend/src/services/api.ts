import axios from 'axios';

const defaultApiBaseURL =
  typeof window !== 'undefined'
    ? import.meta.env.PROD
      ? window.location.origin
      : `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://localhost:8000';

const apiBaseURL = import.meta.env.VITE_API_URL || defaultApiBaseURL;

const api = axios.create({
  baseURL: apiBaseURL,
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
    `${apiBaseURL}/auth/refresh`,
    {},
    { withCredentials: true }
  );
};

const logout = () => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('auth-failed'));
  }
};

const logoutMaster = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('master_auth');
    localStorage.removeItem('master_user');
    window.dispatchEvent(new Event('master-auth-changed'));
  }
};

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const requestUrl = originalRequest?.url || '';
    const isAuthEndpoint = requestUrl.includes('/auth/login') || requestUrl.includes('/auth/refresh');
    const isMasterEndpoint = requestUrl.startsWith('/master/');

    if (error.response?.status === 401 && isMasterEndpoint) {
      logoutMaster();
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint && !isMasterEndpoint) {
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
