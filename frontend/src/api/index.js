import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
const API_V1_STR = '/api/v1';
const TOKEN_STORAGE_KEY = 'gridforge_token';

// Dispatched on `window` whenever the app decides the current session is
// no longer valid - either reactively (any API call comes back 401) or
// proactively (the stored JWT's own exp claim has passed). App.js listens
// for this to bounce back to the Login view from anywhere, not just the
// one component whose request happened to trigger it.
export const AUTH_EXPIRED_EVENT = 'gridforge:auth-expired';

const apiClient = axios.create({
    baseURL: `${API_URL}${API_V1_STR}`,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Attaches the JWT (if we have one) to every outgoing request.
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem(TOKEN_STORAGE_KEY);
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        console.log(`Sending request to: ${config.url}`, config);
        return config;
    },
    (error) => {
        console.error('Request error:', error);
        return Promise.reject(error);
    }
);

apiClient.interceptors.response.use(
    (response) => {
        console.log(`Received response from: ${response.config.url}`, response);
        return response;
    },
    (error) => {
        console.error('Response error:', error.response || error.message);
        if (error.response?.status === 401) {
            // /auth/login itself returns 401 for a plain wrong-password
            // attempt - that's not a session expiring, it's a login that
            // never succeeded in the first place, and firing the global
            // event for it would stomp the Login form's own "incorrect
            // password" message with a misleading "session expired" one.
            // Every OTHER 401 (submit-project, /results, delete, etc.)
            // means a token that used to work no longer does.
            const isLoginAttempt = error.config?.url?.includes('/auth/login');
            localStorage.removeItem(TOKEN_STORAGE_KEY);
            if (!isLoginAttempt) {
                window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
            }
        }
        return Promise.reject(error);
    }
);

// Reads a JWT's payload without verifying its signature - fine for a
// client-side UX decision ("does this look worth proactively treating as
// expired"), NOT a substitute for real verification, which only the
// backend does. Never use the result of this for an authorization
// decision, only to avoid firing requests we already know will 401.
const decodeJwtPayload = (token) => {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(base64));
    } catch {
        return null;
    }
};

export const isAuthenticated = () => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) return false;
    const decoded = decodeJwtPayload(token);
    // No readable exp claim: can't tell either way from here, so assume
    // valid and let the backend be the real judge on the next request.
    if (!decoded?.exp) return true;
    return decoded.exp * 1000 > Date.now();
};

// EventSource can't set an Authorization header, so the token has to
// travel as a query param instead (see backend's get_current_user_sse).
export const getTaskStreamUrl = () => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) return null;
    return `${API_URL}${API_V1_STR}/stream/tasks?token=${encodeURIComponent(token)}`;
};

export const logout = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
};

// FastAPI's error body isn't always a plain string in `detail` - a 422
// from pydantic validation puts a *list* of {loc, msg, type} objects
// there instead. Every caller of this used to do
// `error.response?.data?.detail || 'fallback'` directly, which for a 422
// would have produced "[object Object]" (string-concatenating a plain
// object, or worse an array of them) instead of an actual message.
const extractErrorMessage = (error, fallback) => {
    const detail = error.response?.data?.detail;
    if (Array.isArray(detail)) {
        return detail.map((d) => d.msg).filter(Boolean).join(' ') || fallback;
    }
    if (typeof detail === 'string') return detail;
    return error.message || fallback;
};

// Tags the thrown Error with the HTTP status (or null for a network
// failure that never got a response at all) so callers can tell "wrong
// password" (401) apart from "rate limited" (429) apart from "the
// server's unreachable" (no status) - a bare Error string can't carry
// that distinction.
const throwWithStatus = (error, fallback) => {
    const err = new Error(extractErrorMessage(error, fallback));
    err.status = error.response?.status ?? null;
    throw err;
};

export const register = async (username, password) => {
    try {
        const response = await apiClient.post('/auth/register', { username, password });
        return response.data;
    } catch (error) {
        console.error('register failed:', error.response?.data || error.message);
        throwWithStatus(error, 'Registration failed.');
    }
};

export const login = async (username, password) => {
    // The backend's /auth/login uses FastAPI's OAuth2PasswordRequestForm,
    // which expects standard form-encoding, not JSON.
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);

    try {
        const response = await apiClient.post('/auth/login', form, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
        localStorage.setItem(TOKEN_STORAGE_KEY, response.data.access_token);
        return response.data;
    } catch (error) {
        console.error('login failed:', error.response?.data || error.message);
        throwWithStatus(error, 'Login failed.');
    }
};

export const uploadProject = async (file, onProgress) => {
    console.log("Starting project upload with axios...");
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await apiClient.post('/submit-project', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            onUploadProgress: (progressEvent) => {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                if (onProgress) {
                    onProgress(percentCompleted);
                }
            },
        });
        console.log("Upload successful, response data:", response.data);
        return response.data;
    } catch (error) {
        console.error("Axios upload failed:", error.response?.data || error.message);
        throwWithStatus(error, 'Upload failed via axios.');
    }
};

export const deleteTask = async (taskId) => {
    console.log(`Deleting task: ${taskId}...`);
    try {
        await apiClient.delete(`/task/${taskId}`);
    } catch (error) {
        console.error(`deleteTask ${taskId} failed:`, error.response?.data || error.message);
        throwWithStatus(error, `Failed to delete task ${taskId}.`);
    }
};
