import React, { useState, useEffect, useCallback } from 'react';
import { getTasks } from '../api';
import useTaskPoller from '../hooks/useTaskPoller';
import TaskItem from './TaskItem';

const Dashboard = ({ newTaskId }) => {
    const [tasks, setTasks] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchTasks = useCallback(async () => {
        try {
            const allTasks = await getTasks();
            // Sort by creation date, newest first
            allTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            setTasks(allTasks);
        } catch (err) {
            setError('Failed to load tasks. Is the backend running?');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTasks();
    }, [fetchTasks, newTaskId]);

    const updatedTasks = useTaskPoller(tasks);

    if (loading) {
        return <div className="text-center p-8">Loading tasks...</div>;
    }

    if (error) {
        return <div className="bg-red-900 border border-red-600 text-white px-4 py-3 rounded-md">{error}</div>;
    }

    return (
        <div className="bg-gray-800 rounded-lg shadow-xl p-6">
            <h2 className="text-2xl font-semibold mb-4 border-b border-gray-700 pb-2">Task Dashboard</h2>
            <div className="space-y-4">
                {updatedTasks.length > 0 ? (
                    updatedTasks.map(task => <TaskItem key={task.id} task={task} />)
                ) : (
                    <p className="text-gray-400">No tasks submitted yet. Upload a project to get started.</p>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
