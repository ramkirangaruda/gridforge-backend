import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
const API_V1_STR = '/api/v1';
const TOKEN_STORAGE_KEY = 'gridforge_token';

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
            // Token missing/expired/invalid - clear it so the UI can fall
            // back to a logged-out state instead of retrying with a stale
            // token forever.
            localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
        return Promise.reject(error);
    }
);

export const isAuthenticated = () => !!localStorage.getItem(TOKEN_STORAGE_KEY);

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

export const register = async (username, password) => {
    try {
        const response = await apiClient.post('/auth/register', { username, password });
        return response.data;
    } catch (error) {
        console.error('register failed:', error.response?.data || error.message);
        throw new Error(error.response?.data?.detail || 'Registration failed.');
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
        throw new Error(error.response?.data?.detail || 'Login failed.');
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
        throw new Error(error.response?.data?.detail || 'Upload failed via axios.');
    }
};

export const getTasks = async () => {
    console.log("Fetching all tasks...");
    try {
        const response = await apiClient.get('/results');
        console.log("getTasks response:", response.data);
        return response.data;
    } catch (error) {
        console.error("getTasks failed:", error.response?.data || error.message);
        throw new Error(error.response?.data?.detail || 'Failed to fetch tasks.');
    }
};

export const getTask = async (taskId) => {
    console.log(`Fetching task: ${taskId}...`);
    try {
        const response = await apiClient.get(`/task/${taskId}`);
        console.log(`getTask ${taskId} response:`, response.data);
        return response.data;
    } catch (error) {
        console.error(`getTask ${taskId} failed:`, error.response?.data || error.message);
        throw new Error(error.response?.data?.detail || `Failed to fetch task ${taskId}.`);
    }
};
