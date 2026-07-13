import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
const API_V1_STR = '/api/v1';

const apiClient = axios.create({
    baseURL: `${API_URL}${API_V1_STR}`,
    headers: {
        'Content-Type': 'application/json',
    },
});

apiClient.interceptors.request.use(
    (config) => {
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
        return Promise.reject(error);
    }
);


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
