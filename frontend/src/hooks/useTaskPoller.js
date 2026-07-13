import { useState, useEffect, useRef } from 'react';
import { getTask } from '../api';

const useTaskPoller = (initialTasks) => {
    const [tasks, setTasks] = useState(initialTasks);
    const intervalRef = useRef(null);

    useEffect(() => {
        setTasks(initialTasks);
    }, [initialTasks]);

    const poll = async () => {
        const tasksToPoll = tasks.filter(t => ['queued', 'running'].includes(t.status));
        if (tasksToPoll.length === 0) {
            return;
        }

        const updatedTasks = await Promise.all(
            tasks.map(async (task) => {
                if (['queued', 'running'].includes(task.status)) {
                    try {
                        return await getTask(task.id);
                    } catch (error) {
                        console.error(`Failed to poll task ${task.id}:`, error);
                        // Keep the old task data if polling fails
                        return task;
                    }
                }
                return task;
            })
        );
        setTasks(updatedTasks);
    };

    useEffect(() => {
        // Clear existing interval
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
        }

        // Start a new interval
        intervalRef.current = setInterval(poll, 3000); // Poll every 3 seconds

        // Cleanup on unmount
        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, [tasks]); // Rerun effect if tasks change

    return tasks;
};

export default useTaskPoller;
